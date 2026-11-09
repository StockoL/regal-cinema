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
