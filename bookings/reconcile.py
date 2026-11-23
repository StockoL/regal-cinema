"""The scheduled check: payments, holds and bookings left behind when
something didn't finish (architecture 4.32). Every step is safe to run
twice."""

from datetime import timedelta

from django.utils import timezone

from accounts.models import get_system_user
from payments.base import PaymentUnavailable

from .models import Booking, SeatHold
from .services import recheck_payment

# Younger sessions are left to the webhook; older ones have long since
# expired unpaid, or been settled.
STUCK_FROM = timedelta(minutes=10)
STUCK_UNTIL = timedelta(hours=24)
# How long an expired hold, and a pending booking that was never paid,
# are kept before they're cleared away.
HOLDS_KEPT_FOR = timedelta(hours=24)
ABANDONED_AFTER = timedelta(days=7)


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


def tidy_up():
    """Delete holds that expired over a day ago, and pending bookings
    over a week old with their holds. Lazy expiry already frees the
    seats (4.8), so this only keeps the tables small. A booking with a
    refund, a sold seat, a cancellation or an audit entry is kept,
    because money or history is attached to it. Returns the counts."""
    now = timezone.now()
    holds, _ = SeatHold.objects.filter(
        expires_at__lt=now - HOLDS_KEPT_FOR,
    ).delete()
    _, deleted = Booking.objects.filter(
        status=Booking.Status.PENDING,
        created_at__lt=now - ABANDONED_AFTER,
        refunds__isnull=True, seats__isnull=True,
        cancellations__isnull=True, audit_entries__isnull=True,
    ).delete()
    return {'holds': holds, 'bookings': deleted.get('bookings.Booking', 0)}
