from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from bookings.basket import BasketError
from bookings.models import Booking, SeatHold
from bookings.services import (
    HoldTimeUsedUp,
    SeatsUnavailable,
    amend_booking,
    cancel_pending_booking,
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


class CancelPendingBookingTests(TestCase):

    def test_only_a_pending_booking_can_be_let_go(self):
        """A paid booking is cancelled through staff, with a record of
        who and why (4.22), never by deleting it."""
        screening, _ = make_screening()
        booking = Booking.objects.create(
            screening=screening, status=Booking.Status.PAID
        )
        with self.assertRaises(ValueError):
            cancel_pending_booking(booking)
        self.assertTrue(Booking.objects.exists())


@override_settings(SEAT_HOLD_MINUTES=10)
class AmendBookingTests(TestCase):
    """Going back and changing anything before paying, without starting
    again. Journey 2, "Amend"; architecture 4.8 steps 11 and 12."""

    def setUp(self):
        self.screening, (self.seat_1, self.seat_2) = make_screening()
        self.seat_3 = Seat.objects.create(
            screen=self.screening.screen, layout=self.screening.layout,
            area=Seat.Area.STALLS, number=3, row_index=0, column_index=3,
        )
        film = self.screening.film
        film.age_rating = 'PG'
        film.save()
        self.adult = TicketType.objects.get(name='Adult')
        self.student = TicketType.objects.get(name='Student')
        self.booking = start_booking(
            self.screening, [(self.seat_1, self.adult),
                             (self.seat_2, self.adult)], 0, 'session-a',
        )

    def amend(self, choices, infants=0):
        return amend_booking(self.booking, choices, infants, 'session-a')

    def held(self):
        return {(h.seat, h.ticket_type) for h in self.booking.holds.all()}

    def test_seats_can_be_swapped_in_one_step(self):
        self.amend([(self.seat_1, self.adult), (self.seat_3, self.adult)])
        self.assertEqual(self.held(), {(self.seat_1, self.adult),
                                       (self.seat_3, self.adult)})

    def test_a_removed_seat_is_free_to_others_at_once(self):
        """Journey 2, "Seats never stuck"."""
        self.amend([(self.seat_1, self.adult)])
        hold_seats(self.screening, [(self.seat_2, self.adult)], 'session-b')

    def test_ticket_types_and_infants_can_change(self):
        self.amend([(self.seat_1, self.student), (self.seat_2, self.adult)],
                   infants=2)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.infant_count, 2)
        self.assertIn((self.seat_1, self.student), self.held())

    def test_each_change_restarts_the_timer(self):
        SeatHold.objects.update(expires_at=timezone.now() + timedelta(
            minutes=1))
        before = timezone.now()
        self.amend([(self.seat_1, self.adult), (self.seat_2, self.adult)])
        for hold in self.booking.holds.all():
            self.assertGreater(hold.expires_at,
                               before + timedelta(minutes=9))

    def test_the_timer_never_runs_past_thirty_minutes(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            created_at=timezone.now() - timedelta(minutes=25)
        )
        self.booking.refresh_from_db()
        self.amend([(self.seat_1, self.adult), (self.seat_2, self.adult)])
        cap = self.booking.created_at + timedelta(minutes=30)
        for hold in self.booking.holds.all():
            self.assertLessEqual(hold.expires_at, cap)

    def test_once_the_thirty_minutes_are_up_it_must_start_again(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            created_at=timezone.now() - timedelta(minutes=31)
        )
        self.booking.refresh_from_db()
        with self.assertRaises(HoldTimeUsedUp):
            self.amend([(self.seat_1, self.adult)])

    def test_a_taken_seat_leaves_the_booking_as_it_was(self):
        hold_seats(self.screening, [(self.seat_3, self.adult)], 'session-b')
        with self.assertRaises(SeatsUnavailable) as caught:
            self.amend([(self.seat_1, self.adult), (self.seat_3, self.adult)])
        self.assertEqual(caught.exception.seats, [self.seat_3])
        self.assertEqual(self.held(), {(self.seat_1, self.adult),
                                       (self.seat_2, self.adult)})

    def test_a_broken_rule_leaves_the_booking_as_it_was(self):
        child = TicketType.objects.get(name='Child')
        with self.assertRaises(BasketError):
            self.amend([(self.seat_1, child)])
        self.assertEqual(len(self.held()), 2)
