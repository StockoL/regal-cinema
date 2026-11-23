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
    # The pending booking these seats are for, once the customer has
    # proceeded to checkout (4.2).
    booking = models.ForeignKey(
        'Booking', on_delete=models.CASCADE, related_name='holds',
        null=True, blank=True,
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


# No 0, O, 1, I or L, which are easy to mishear over the phone.
REFERENCE_CHARACTERS = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


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
    # The Stripe Checkout Session paying for an online booking. Unique,
    # so the webhook can only ever find one booking for it (4.13).
    stripe_checkout_session_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    # The payment, set once Stripe says it went through (4.13). A refund
    # goes back against the payment intent.
    stripe_payment_intent_id = models.CharField(
        max_length=255, null=True, blank=True
    )
    amount_charged_pence = models.PositiveIntegerField(null=True, blank=True)
    # What Stripe kept and what the venue received, looked up after the
    # booking is confirmed, so a failed lookup never undoes it (4.13).
    stripe_fee_pence = models.PositiveIntegerField(null=True, blank=True)
    stripe_net_pence = models.IntegerField(null=True, blank=True)
    # The staff member who took an in-venue booking (4.14).
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='bookings_taken', null=True, blank=True,
    )
    # Under 2s, free and on a lap, so they have no seat (4.2).
    infant_count = models.PositiveSmallIntegerField(default=0)
    # How many seats the customer chose, so confirming can tell if a
    # hold ran out and its seat went to someone else (4.32).
    seat_count = models.PositiveSmallIntegerField(default=0)
    # Set once, when payment is confirmed. Indexed for the reports,
    # which go by payment date (4.28, 4.33).
    paid_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        # Each sensitive staff action has its own permission (4.9).
        permissions = [
            ('view_bookings', 'Can look up bookings and guest lists'),
            ('check_in_booking', 'Can check a party in'),
            ('create_in_venue_booking', 'Can take a booking at the venue'),
            ('cancel_booking', 'Can approve, decline or cancel a booking'),
            ('refund_booking', 'Can refund a booking to the card'),
            ('view_attention', 'Can see what needs attention'),
        ]

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


class Cancellation(models.Model):
    """One cancellation of a booking, whoever started it, so a declined
    request and a customer's choice of refund over voucher both have
    somewhere to be recorded (4.2, 4.11, 4.22)."""

    class Kind(models.TextChoices):
        CUSTOMER_REQUEST = 'customer_request', 'Customer request'
        SCREENING_CANCELLED = 'screening_cancelled', 'Screening cancelled'

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested'
        APPROVED = 'approved', 'Approved'
        DECLINED = 'declined', 'Declined'

    class Outcome(models.TextChoices):
        VOUCHER = 'voucher', 'Voucher'
        REFUND = 'refund', 'Refund'

    booking = models.ForeignKey(
        Booking, on_delete=models.PROTECT, related_name='cancellations'
    )
    kind = models.CharField(max_length=25, choices=Kind.choices)
    reason = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.REQUESTED)
    # Empty until staff decide.
    outcome = models.CharField(max_length=10, choices=Outcome.choices,
                               blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name='cancellations_decided', null=True, blank=True,
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    # The venue's cancellation fee taken off the voucher, as it was then.
    fee_pence = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.get_kind_display()} for {self.booking.reference}'


class StripeEvent(models.Model):
    """A Stripe event that has been handled. Stripe can send the same
    event more than once, and one already here is ignored (4.13)."""

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.event_type} {self.event_id}'


class Refund(models.Model):
    """One refund against a booking's payment. It's created pending,
    sent to the provider once the transaction has committed, and then
    marked succeeded or failed. A failed one is kept, so it can be
    retried and shown to staff (4.2, 4.32)."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'

    booking = models.ForeignKey(
        Booking, on_delete=models.PROTECT, related_name='refunds'
    )
    amount_pence = models.PositiveIntegerField()
    reason = models.CharField(max_length=200)
    # The payment this refunds: usually the booking's own, but a second
    # payment for a booking already paid is refunded against itself.
    stripe_payment_intent_id = models.CharField(max_length=255)
    stripe_refund_id = models.CharField(max_length=255, null=True,
                                        blank=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.PENDING)
    # The provider's message when a refund fails.
    error = models.TextField(blank=True)
    # A member of staff, or the system user for an automatic refund.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='refunds_made',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.amount_pence}p refund for {self.booking.reference}'


class OutboundEmail(models.Model):
    """An email waiting to go, or gone. It's written in the same
    transaction as the change it reports and sent after the commit, so
    a failed send never undoes a booking, and it can be tried again
    (4.2, 4.32)."""

    class Kind(models.TextChoices):
        CONFIRMATION = 'confirmation', 'Confirmation'
        REMINDER = 'reminder', 'Reminder'
        CANCELLATION = 'cancellation', 'Cancellation'
        REFUND_ISSUED = 'refund_issued', 'Refund issued'
        SCREENING_CANCELLED = 'screening_cancelled', 'Screening cancelled'
        VOUCHER_ISSUED = 'voucher_issued', 'Voucher issued'
        MEMBERSHIP_RENEWAL = 'membership_renewal', 'Membership renewal'

    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    kind = models.CharField(max_length=25, choices=Kind.choices)
    # Not every email is about a booking, and losing the link is
    # harmless, since the email stands on its own (4.21).
    booking = models.ForeignKey(
        Booking, on_delete=models.SET_NULL, related_name='emails',
        null=True, blank=True,
    )
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    text_body = models.TextField()
    html_body = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # Sending one twice would confuse a customer.
            models.UniqueConstraint(
                fields=['booking', 'kind'],
                condition=models.Q(kind__in=[
                    'confirmation', 'reminder', 'cancellation',
                ]),
                name='one_of_each_booking_email',
            ),
        ]

    def __str__(self):
        return f'{self.get_kind_display()} to {self.recipient}'


class SeatBookingQuerySet(models.QuerySet):

    def live(self):
        """Sales that haven't been released."""
        return self.filter(released_at__isnull=True)


class SeatBooking(models.Model):
    """A sold seat. Releasing it sets `released_at` instead of deleting
    the row, so the sale stays on record (architecture 4.2, 4.8)."""

    booking = models.ForeignKey(
        Booking, on_delete=models.PROTECT, related_name='seats'
    )
    # Copied from the booking, so the database can refuse a second live
    # sale of the same seat for the same screening.
    screening = models.ForeignKey(
        'screenings.Screening', on_delete=models.PROTECT,
        related_name='seat_bookings',
    )
    seat = models.ForeignKey(
        'screenings.Seat', on_delete=models.PROTECT,
        related_name='seat_bookings',
    )
    ticket_type = models.ForeignKey(
        'screenings.TicketType', on_delete=models.PROTECT,
        related_name='seat_bookings',
    )
    # Snapshots taken when sold, never worked out again.
    price_pence = models.PositiveIntegerField()
    vat_rate_percent = models.PositiveSmallIntegerField()
    released_at = models.DateTimeField(null=True, blank=True)

    objects = SeatBookingQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['screening', 'seat'],
                condition=models.Q(released_at__isnull=True),
                name='one_live_sale_per_seat',
            ),
        ]

    def __str__(self):
        return f'{self.seat} sold for {self.screening}'
