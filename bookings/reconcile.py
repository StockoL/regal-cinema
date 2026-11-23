"""The scheduled check: payments, holds and bookings left behind when
something didn't finish (architecture 4.32). Every step is safe to run
twice."""

from datetime import timedelta

from django.utils import timezone

from accounts.models import get_system_user
from payments.base import PaymentUnavailable

from .models import Booking
from .services import recheck_payment

# Younger sessions are left to the webhook; older ones have long since
# expired unpaid, or been settled.
STUCK_FROM = timedelta(minutes=10)
STUCK_UNTIL = timedelta(hours=24)


def recheck_stuck_payments():
    """Ask Stripe about every pending booking whose session started
    between 10 minutes and 24 hours ago, confirming any that were paid
    under the system user. One that Stripe can't answer for is skipped
    until the next run. Returns the counts."""
    now = timezone.now()
    stuck = Booking.objects.filter(
        status=Booking.Status.PENDING,
        checkout_started_at__lte=now - STUCK_FROM,
        checkout_started_at__gte=now - STUCK_UNTIL,
    )
    counts = {'checked': 0, 'paid': 0, 'unreachable': 0}
    system = get_system_user()
    for booking in stuck:
        counts['checked'] += 1
        try:
            if recheck_payment(booking, system,
                               'Paid on Stripe with no webhook. Found by '
                               'the scheduled check.'):
                counts['paid'] += 1
        except PaymentUnavailable:
            counts['unreachable'] += 1
    return counts
