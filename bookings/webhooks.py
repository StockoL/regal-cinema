from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.models import get_system_user
from payments import get_provider
from payments.base import InvalidSignature
from staff.audit import log_action
from staff.models import AuditLogEntry

from .models import Booking, StripeEvent
from .services import (
    SeatsLost,
    confirm_booking,
    record_payment_fee,
    refund_duplicate_payment,
    refund_late_payment,
)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Stripe's word on a payment, and the only thing that marks a
    booking paid (4.13 step 5). The signature is checked before anything
    in the request is trusted, and each event is handled once. If
    handling fails, the event isn't recorded either, so Stripe sends it
    again."""
    try:
        event = get_provider().parse_webhook(
            request.body, request.headers.get('Stripe-Signature', '')
        )
    except InvalidSignature:
        return HttpResponseBadRequest()
    with transaction.atomic():
        _, new = StripeEvent.objects.get_or_create(
            event_id=event.id, defaults={'event_type': event.type},
        )
        if new and event.type in HANDLERS:
            HANDLERS[event.type](event.object)
    return HttpResponse()


def session_completed(session):
    if session.get('payment_status') != 'paid':
        return
    booking = paid_for(session)
    if booking is None:
        return
    if booking.status != Booking.Status.PENDING:
        # Already settled. A different payment is a second one (4.32).
        if session.get('payment_intent') != booking.stripe_payment_intent_id:
            refund_duplicate_payment(booking, session.get('payment_intent'),
                                     session.get('amount_total'))
        return
    # Recorded before confirming, so a refund can find the payment even
    # if the seats turn out to be lost.
    booking.stripe_payment_intent_id = session.get('payment_intent')
    booking.amount_charged_pence = session.get('amount_total')
    booking.save(update_fields=['stripe_payment_intent_id',
                                'amount_charged_pence'])
    try:
        confirm_booking(booking)
    except SeatsLost:
        refund_late_payment(booking)
    else:
        transaction.on_commit(lambda: record_payment_fee(booking.pk))


def paid_for(session):
    """The booking a session paid for. Usually it holds that session, but
    if its basket changed after Pay it holds a newer one, so the booking
    reference every session carries finds it instead (4.32)."""
    by_session = Booking.objects.filter(
        stripe_checkout_session_id=session['id']
    ).first()
    if by_session is not None or not session.get('client_reference_id'):
        return by_session
    return Booking.objects.filter(
        reference=session['client_reference_id']
    ).first()


def dispute_opened(dispute):
    """The customer's bank has opened a chargeback (4.13). The booking is
    flagged for staff and logged, and nothing is cancelled."""
    booking = Booking.objects.filter(
        stripe_payment_intent_id=dispute.get('payment_intent')
    ).first()
    if booking is None or booking.disputed_at is not None:
        return
    booking.disputed_at = timezone.now()
    booking.save(update_fields=['disputed_at'])
    log_action(get_system_user(), AuditLogEntry.Action.DISPUTE_OPENED,
               f"The customer's bank opened a dispute, reason: "
               f"{dispute.get('reason') or 'not given'}.",
               booking=booking)


def dispute_closed(dispute):
    """The dispute is settled, and the log says how it ended."""
    booking = Booking.objects.filter(
        stripe_payment_intent_id=dispute.get('payment_intent')
    ).first()
    if booking is None or booking.dispute_closed_at is not None:
        return
    booking.dispute_closed_at = timezone.now()
    booking.save(update_fields=['dispute_closed_at'])
    log_action(get_system_user(), AuditLogEntry.Action.DISPUTE_CLOSED,
               f"The dispute closed: {dispute.get('status') or 'unknown'}.",
               booking=booking)


# What each Stripe event does. Any other event is recorded and ignored.
HANDLERS = {
    'checkout.session.completed': session_completed,
    'charge.dispute.created': dispute_opened,
    'charge.dispute.closed': dispute_closed,
}
