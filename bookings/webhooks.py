from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from payments import get_provider
from payments.base import InvalidSignature

from .models import Booking, StripeEvent
from .services import SeatsLost, confirm_booking, refund_late_payment


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
        if new and event.type == 'checkout.session.completed':
            session_completed(event.object)
    return HttpResponse()


def session_completed(session):
    if session.get('payment_status') != 'paid':
        return
    booking = paid_for(session)
    if booking is None:
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
