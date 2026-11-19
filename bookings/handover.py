"""Held seats survive logging in mid-checkout (architecture 4.16).

Django gives the session a new key when someone logs in, and holds are
tied to that key. The session's data is kept, though, so each booking
started in it is remembered there, and at login those bookings and
their holds move to the account and the new key."""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import Booking, SeatHold

SESSION_BOOKINGS = 'bookings'


def remember_booking(request, booking):
    references = request.session.get(SESSION_BOOKINGS, [])
    if booking.reference not in references:
        request.session[SESSION_BOOKINGS] = references + [booking.reference]


@receiver(user_logged_in)
def claim_bookings(sender, request, user, **kwargs):
    bookings = Booking.objects.filter(
        reference__in=request.session.get(SESSION_BOOKINGS, []),
        status=Booking.Status.PENDING, user__isnull=True,
    )
    SeatHold.objects.filter(booking__in=bookings).update(
        user=user, session_key=request.session.session_key,
    )
    bookings.update(user=user)
