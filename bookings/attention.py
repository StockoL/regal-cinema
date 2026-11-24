"""What needs a person: the needs-attention page's lists (architecture
4.32). Each is a query, so the page and its count stay cheap."""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Booking, OutboundEmail, Refund
from .reconcile import STUCK_UNTIL
from .services import RECHECK_AFTER

# The scheduled check runs about hourly, so an email still queued after
# this long has failed a retry, or the retry never ran.
EMAIL_WAITED_TOO_LONG = timedelta(hours=1)


def stuck_payments():
    """Pending bookings whose session started between five minutes and
    a day ago: long enough for the webhook to have come, recent enough
    that the customer may have paid."""
    now = timezone.now()
    return (
        Booking.objects.filter(
            status=Booking.Status.PENDING,
            checkout_started_at__lte=now - RECHECK_AFTER,
            checkout_started_at__gte=now - STUCK_UNTIL,
        )
        .select_related('screening__film', 'user')
        .order_by('checkout_started_at')
    )


def unsent_emails():
    """Emails the outbox gave up on, and ones still queued an hour after
    they were written."""
    return (
        OutboundEmail.objects.filter(
            Q(status=OutboundEmail.Status.FAILED)
            | Q(status=OutboundEmail.Status.QUEUED,
                created_at__lt=timezone.now() - EMAIL_WAITED_TOO_LONG)
        )
        .select_related('booking')
        .order_by('created_at')
    )


def failed_refunds():
    """Refunds Stripe refused. The scheduled check sends each again, so
    one still here is likely to need a person."""
    return (
        Refund.objects.filter(status=Refund.Status.FAILED)
        .select_related('booking')
        .order_by('created_at')
    )


def open_disputes():
    """Bookings whose payment the customer's bank is disputing. The
    venue answers in Stripe's dashboard, and nothing here changes until
    the dispute closes (4.13)."""
    return (
        Booking.objects.filter(disputed_at__isnull=False,
                               dispute_closed_at__isnull=True)
        .select_related('screening__film', 'user')
        .order_by('disputed_at')
    )
