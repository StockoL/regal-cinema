import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from bookings.models import REFERENCE_CHARACTERS

# Every voucher, bought or issued for a cancelled booking (4.4).
VOUCHER_LIFETIME = timedelta(days=365)


def new_voucher_code():
    """Twelve characters in three groups. The code alone spends the
    balance, like a gift card, so it has to be unguessable (4.26), and
    it uses the booking references' alphabet, which is easy to read
    out over the phone."""
    groups = [''.join(secrets.choice(REFERENCE_CHARACTERS) for _ in range(4))
              for _ in range(3)]
    return '-'.join(groups)


class Voucher(models.Model):
    """A balance whoever holds the code can spend, drawn down across
    bookings until it reaches zero (4.4, 4.10)."""

    class Source(models.TextChoices):
        PURCHASED = 'purchased', 'Purchased'
        SCREENING_CANCELLED = 'screening_cancelled', 'Screening cancelled'
        BOOKING_CANCELLED = 'booking_cancelled', 'Booking cancelled'

    code = models.CharField(max_length=14, unique=True, editable=False)
    initial_value_pence = models.PositiveIntegerField()
    remaining_value_pence = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    source = models.CharField(max_length=25, choices=Source.choices)
    # Who bought it, for the record only: it isn't tied to them for
    # spending (4.4).
    purchased_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='vouchers_bought', null=True, blank=True,
    )
    stripe_checkout_session_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    stripe_payment_intent_id = models.CharField(max_length=255, null=True,
                                                blank=True)
    # The booking a voucher was issued in place of.
    source_booking = models.ForeignKey(
        'bookings.Booking', on_delete=models.SET_NULL,
        related_name='vouchers_issued', null=True, blank=True,
    )
    # A bought voucher starts inactive until Stripe confirms (4.26).
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    remaining_value_pence__lte=models.F('initial_value_pence')
                ),
                name='voucher_balance_within_its_value',
            ),
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = new_voucher_code()
        if self.expires_at is None:
            self.expires_at = timezone.now() + VOUCHER_LIFETIME
        super().save(*args, **kwargs)

    @property
    def is_usable(self):
        return (self.is_active and self.remaining_value_pence > 0
                and self.expires_at > timezone.now())
