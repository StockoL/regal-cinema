"""What needs a person: the needs-attention page's lists (architecture
4.32). Each is a query, so the page and its count stay cheap."""

from django.utils import timezone

from .models import Booking
from .reconcile import STUCK_UNTIL
from .services import RECHECK_AFTER


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
