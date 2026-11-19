from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from payments import get_provider
from payments.base import InvalidSignature

from .models import Booking, StripeEvent
from .services import confirm_booking


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
    booking = Booking.objects.filter(
        stripe_checkout_session_id=session['id']
    ).first()
    if booking is not None:
        confirm_booking(booking)
