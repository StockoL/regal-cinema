from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from bookings.basket import BasketError
from bookings.models import Booking, SeatHold
from bookings.services import (
    SeatsUnavailable,
    hold_seats,
    start_booking,
)
from bookings.tests.test_holds import make_screening
from screenings.models import ScreeningClosedArea, Seat, TicketType


@override_settings(SEAT_HOLD_MINUTES=10)
class HoldSeatsTests(TestCase):
    """Holding the chosen seats in one step, all or none. Journey 2,
    "Hold created" and "Conflict"; architecture 4.8 step 3 and 4."""

    def setUp(self):
        self.screening, (self.seat_1, self.seat_2) = make_screening()
        self.adult = TicketType.objects.get(name='Adult')
        self.student = TicketType.objects.get(name='Student')

    def hold(self, choices, session_key='session-a', **kwargs):
        return hold_seats(self.screening, choices, session_key, **kwargs)

    def held_by_someone_else(self, seat, minutes=10):
        SeatHold.objects.create(
            screening=self.screening, seat=seat, ticket_type=self.adult,
            session_key='session-b',
            expires_at=timezone.now() + timedelta(minutes=minutes),
        )

    def test_each_seat_is_held_with_its_ticket_type(self):
        holds = self.hold([(self.seat_1, self.adult),
                           (self.seat_2, self.student)])
        self.assertEqual(
            {(h.seat, h.ticket_type) for h in holds},
            {(self.seat_1, self.adult), (self.seat_2, self.student)},
        )

    def test_holds_last_the_venues_hold_time(self):
        before = timezone.now()
        hold, = self.hold([(self.seat_1, self.adult)])
        self.assertAlmostEqual(
            hold.expires_at, before + timedelta(minutes=10),
            delta=timedelta(seconds=5),
        )

    def test_holds_belong_to_the_session_and_any_user(self):
        user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        hold, = self.hold([(self.seat_1, self.adult)], user=user)
        self.assertEqual((hold.session_key, hold.user), ('session-a', user))

    def test_a_taken_seat_is_named_and_nothing_is_held(self):
        """Only the conflicting seat is reported, so the page can mark
        just that one and keep the customer's other choices."""
        self.held_by_someone_else(self.seat_2)
        with self.assertRaises(SeatsUnavailable) as caught:
            self.hold([(self.seat_1, self.adult), (self.seat_2, self.adult)])
        self.assertEqual(caught.exception.seats, [self.seat_2])
        self.assertFalse(
            SeatHold.objects.filter(session_key='session-a').exists()
        )

    def test_an_expired_hold_doesnt_block_and_is_cleared(self):
        self.held_by_someone_else(self.seat_1, minutes=-1)
        self.hold([(self.seat_1, self.adult)])
        self.assertFalse(
            SeatHold.objects.filter(session_key='session-b').exists()
        )

    def test_a_seat_in_a_closed_area_cant_be_held(self):
        """Journey 2, "Outside section"."""
        circle = Seat.objects.create(
            screen=self.screening.screen, area=Seat.Area.CIRCLE,
            row_label='A', number=1, row_index=0, column_index=0,
        )
        ScreeningClosedArea.objects.create(
            screening=self.screening, area=Seat.Area.CIRCLE
        )
        with self.assertRaises(SeatsUnavailable) as caught:
            self.hold([(circle, self.adult)])
        self.assertEqual(caught.exception.seats, [circle])

    def test_a_seat_out_of_use_cant_be_held(self):
        self.seat_1.is_active = False
        self.seat_1.save()
        with self.assertRaises(SeatsUnavailable):
            self.hold([(self.seat_1, self.adult)])

    def test_a_ticket_type_the_rating_rules_out_is_refused(self):
        """Journey 2, "Ticket types by rating"."""
        film = self.screening.film
        film.age_rating = '18'
        film.save()
        child = TicketType.objects.get(name='Child')
        with self.assertRaises(ValueError):
            self.hold([(self.seat_1, child)])
        self.assertFalse(SeatHold.objects.exists())


@override_settings(SEAT_HOLD_MINUTES=10)
class StartBookingTests(TestCase):
    """Proceeding to checkout: the basket is checked, the seats held and
    a pending booking made, all in one step or not at all (architecture
    4.8 step 3)."""

    def setUp(self):
        self.screening, (self.seat_1, self.seat_2) = make_screening()
        film = self.screening.film
        film.age_rating = 'PG'
        film.save()
        self.adult = TicketType.objects.get(name='Adult')
        self.child = TicketType.objects.get(name='Child')

    def start(self, choices, infants=0, **kwargs):
        return start_booking(self.screening, choices, infants,
                             'session-a', **kwargs)

    def test_makes_a_pending_booking_holding_the_seats(self):
        user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        booking = self.start([(self.seat_1, self.adult),
                              (self.seat_2, self.child)], infants=1,
                             user=user)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual((booking.user, booking.infant_count), (user, 1))
        self.assertEqual(
            {(h.seat, h.ticket_type) for h in booking.holds.all()},
            {(self.seat_1, self.adult), (self.seat_2, self.child)},
        )

    def test_a_basket_that_breaks_a_rule_makes_nothing(self):
        with self.assertRaises(BasketError):
            self.start([(self.seat_1, self.child)])
        self.assertFalse(Booking.objects.exists())
        self.assertFalse(SeatHold.objects.exists())

    def test_a_taken_seat_makes_nothing(self):
        SeatHold.objects.create(
            screening=self.screening, seat=self.seat_2,
            ticket_type=self.adult, session_key='session-b',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        with self.assertRaises(SeatsUnavailable):
            self.start([(self.seat_1, self.adult),
                        (self.seat_2, self.adult)])
        self.assertFalse(Booking.objects.exists())
        self.assertEqual(SeatHold.objects.count(), 1)
