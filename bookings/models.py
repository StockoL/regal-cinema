import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class SeatHoldQuerySet(models.QuerySet):

    def live(self):
        """Holds that haven't run out. Nothing deletes an expired hold on
        a timer: it's ignored here and cleared the next time anyone holds
        a seat at that screening (4.8)."""
        return self.filter(expires_at__gt=timezone.now())


class SeatHold(models.Model):
    """A seat kept for one customer for a few minutes while they check
    out. Separate from a sold seat, so an abandoned checkout can never
    block a seat for good (architecture 4.8)."""

    screening = models.ForeignKey(
        'screenings.Screening', on_delete=models.CASCADE,
        related_name='holds',
    )
    seat = models.ForeignKey(
        'screenings.Seat', on_delete=models.CASCADE, related_name='holds'
    )
    ticket_type = models.ForeignKey(
        'screenings.TicketType', on_delete=models.CASCADE,
        related_name='holds',
    )
    # The browser session that made the hold, until the customer logs
    # in, when the hold moves to their account (4.16).
    session_key = models.CharField(max_length=40)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='seat_holds', null=True, blank=True,
    )
    expires_at = models.DateTimeField()

    objects = SeatHoldQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['screening', 'seat'], name='one_hold_per_seat',
            ),
        ]

    def __str__(self):
        return f'{self.seat} held for {self.screening}'


# No 0, O, 1 or I, which are easy to mishear over the phone.
REFERENCE_CHARACTERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def new_reference():
    code = ''.join(secrets.choice(REFERENCE_CHARACTERS) for _ in range(5))
    return f'RGL-{code}'


class Booking(models.Model):
    """One customer's booking for one screening. It starts as pending
    when they proceed to checkout and holds everything that isn't a
    seat; the seats stay as holds until payment is confirmed (4.2).
    Fields for payment, vouchers, membership, food and check-in arrive
    with those features."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        CANCELLATION_REQUESTED = (
            'cancellation_requested', 'Cancellation requested'
        )
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    class Channel(models.TextChoices):
        ONLINE = 'online', 'Online'
        IN_VENUE = 'in_venue', 'In venue'

    class PaymentMethod(models.TextChoices):
        CARD_ONLINE = 'card_online', 'Card online'
        CARD_IN_PERSON = 'card_in_person', 'Card in person'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='bookings', null=True, blank=True,
    )
    screening = models.ForeignKey(
        'screenings.Screening', on_delete=models.PROTECT,
        related_name='bookings',
    )
    reference = models.CharField(max_length=9, unique=True, editable=False)
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.PENDING
    )
    channel = models.CharField(
        max_length=10, choices=Channel.choices, default=Channel.ONLINE
    )
    payment_method = models.CharField(
        max_length=15, choices=PaymentMethod.choices,
        default=PaymentMethod.CARD_ONLINE,
    )
    # The staff member who took an in-venue booking (4.14).
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='bookings_taken', null=True, blank=True,
    )
    # Under 2s, free and on a lap, so they have no seat (4.2).
    infant_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} for {self.screening}'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._unused_reference()
        super().save(*args, **kwargs)

    @staticmethod
    def _unused_reference():
        while True:
            reference = new_reference()
            if not Booking.objects.filter(reference=reference).exists():
                return reference
