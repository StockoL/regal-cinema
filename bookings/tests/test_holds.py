from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from bookings.models import SeatHold
from screenings.models import (
    Film,
    Screen,
    Screening,
    Seat,
    SeatingLayout,
    TicketClass,
    TicketType,
)


def make_screening():
    screen = Screen.objects.create(name='Screen 1')
    layout = SeatingLayout.objects.create(screen=screen, name='Rows')
    screening = Screening.objects.create(
        film=Film.objects.create(title='Nosferatu', duration_minutes=100),
        screen=screen, layout=layout,
        ticket_class=TicketClass.objects.create(name='Standard'),
        date_time=datetime(2026, 12, 5, 19, 0,
                           tzinfo=ZoneInfo('Europe/London')),
    )
    seats = [
        Seat.objects.create(
            screen=screen, layout=layout, area=Seat.Area.STALLS,
            number=number, row_index=0, column_index=number,
        )
        for number in (1, 2)
    ]
    return screening, seats


class SeatHoldTests(TestCase):
    """A seat kept for one customer for a short time while they check
    out (architecture 4.8)."""

    def setUp(self):
        self.screening, (self.seat, self.other_seat) = make_screening()
        self.adult = TicketType.objects.get(name='Adult')

    def hold(self, seat=None, minutes=10, **fields):
        fields.setdefault('session_key', 'session-a')
        return SeatHold.objects.create(
            screening=self.screening, seat=seat or self.seat,
            ticket_type=self.adult,
            expires_at=timezone.now() + timedelta(minutes=minutes),
            **fields,
        )

    def test_a_seat_can_be_held(self):
        hold = self.hold()
        self.assertEqual(hold.ticket_type, self.adult)
        self.assertIsNone(hold.user)

    def test_one_seat_can_only_be_held_once_per_screening(self):
        """The database refuses a second hold, whoever asks."""
        self.hold()
        with self.assertRaises(IntegrityError):
            self.hold(session_key='session-b')

    def test_live_holds_leave_out_expired_ones(self):
        """Holds expire lazily: nothing deletes them on a timer."""
        live = self.hold()
        self.hold(seat=self.other_seat, minutes=-1)
        self.assertEqual(list(SeatHold.objects.live()), [live])

    def test_a_hold_belongs_to_a_user_once_they_log_in(self):
        user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.assertEqual(self.hold(user=user).user, user)

    def test_holds_go_with_their_screening(self):
        """SeatHold is CASCADE on Screening (4.21)."""
        self.hold()
        self.screening.delete()
        self.assertFalse(SeatHold.objects.exists())
