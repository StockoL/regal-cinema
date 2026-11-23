from django.core.exceptions import ValidationError
from django.db import models


class VenueSettings(models.Model):
    """The values a venue is most likely to want to change, in a single
    row (architecture 4.23). The system provides the mechanisms and the
    venue owns the policy. Code never reads the row directly: it calls
    get_settings()."""

    cancellation_cutoff_hours = models.PositiveSmallIntegerField(default=24)
    # Taken off the voucher when a customer cancels, never when the
    # venue cancels (4.22).
    cancellation_fee_pence = models.PositiveIntegerField(default=0)
    seat_hold_minutes = models.PositiveSmallIntegerField(default=10)
    # 0 closes online sales at the listed start time.
    online_sales_close_minutes = models.PositiveSmallIntegerField(default=0)
    # Around each screening, for the no-overlap rule (4.1).
    trailer_minutes = models.PositiveSmallIntegerField(default=20)
    turnaround_minutes = models.PositiveSmallIntegerField(default=15)
    # Whole pounds (4.26).
    gift_voucher_min_pounds = models.PositiveSmallIntegerField(default=10)
    gift_voucher_max_pounds = models.PositiveSmallIntegerField(default=100)
    # How long an unused membership or gift voucher can be refunded.
    withdrawal_days = models.PositiveSmallIntegerField(default=14)
    food_order_cutoff_minutes = models.PositiveSmallIntegerField(default=90)
    bar_collection_minutes_before = models.PositiveSmallIntegerField(
        default=30
    )
    table_service_default = models.BooleanField(default=True)
    # Also caps how many seats one session can hold at once (4.29).
    max_tickets_per_booking = models.PositiveSmallIntegerField(default=10)
    online_sales_paused = models.BooleanField(default=False)
    # From the range Ofcom keeps for drama and fiction: the venue is
    # fictional, so its address is left blank.
    phone = models.CharField(max_length=30, default='01632 960 123')
    address = models.TextField(blank=True)
    opening_hours = models.TextField(blank=True)

    class Meta:
        verbose_name = 'venue settings'
        verbose_name_plural = 'venue settings'
        permissions = [
            ('manage_venue_settings', 'Can change the venue settings'),
        ]

    def __str__(self):
        return 'Venue settings'

    def clean(self):
        if self.gift_voucher_max_pounds < self.gift_voucher_min_pounds:
            raise ValidationError({
                'gift_voucher_max_pounds':
                    'The largest gift voucher must be at least the smallest.',
            })

    def save(self, *args, **kwargs):
        # Always the one row.
        self.pk = 1
        super().save(*args, **kwargs)


def get_settings():
    """The venue's settings. The one place that knows where they come
    from (4.23)."""
    return VenueSettings.objects.get_or_create(pk=1)[0]
