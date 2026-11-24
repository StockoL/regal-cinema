from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bookings.basket import BasketError
from bookings.models import Booking, SeatBooking, SeatHold
from bookings.services import (
    HoldTimeUsedUp,
    HoldsExpired,
    SeatsLost,
    SeatsUnavailable,
    amend_booking,
    cancel_pending_booking,
    confirm_booking,
    hold_seats,
    release_seats,
    start_booking,
    start_payment,
)
from bookings.tests.test_holds import make_screening
from payments.fake import FakeProvider
from screenings.models import (
    ScreeningClosedArea,
    ScreeningPrice,
    Seat,
    TicketType,
)
from venue.models import VenueSettings


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
        """A setting the venue changes in the admin (4.23)."""
        VenueSettings.objects.update(seat_hold_minutes=15)
        before = timezone.now()
        hold, = self.hold([(self.seat_1, self.adult)])
        self.assertAlmostEqual(
            hold.expires_at, before + timedelta(minutes=15),
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

    def sold(self, seat, released_at=None):
        SeatBooking.objects.create(
            booking=Booking.objects.create(screening=self.screening),
            screening=self.screening, seat=seat, ticket_type=self.adult,
            price_pence=950, vat_rate_percent=20, released_at=released_at,
        )

    def test_a_sold_seat_cant_be_held(self):
        self.sold(self.seat_1)
        with self.assertRaises(SeatsUnavailable) as caught:
            self.hold([(self.seat_1, self.adult)])
        self.assertEqual(caught.exception.seats, [self.seat_1])

    def test_a_released_seat_can_be_held_again(self):
        self.sold(self.seat_1, released_at=timezone.now())
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
        self.assertEqual(booking.seat_count, 2)
        self.assertEqual(
            {(h.seat, h.ticket_type) for h in booking.holds.all()},
            {(self.seat_1, self.adult), (self.seat_2, self.child)},
        )

    def test_the_venues_ticket_limit_applies(self):
        VenueSettings.objects.update(max_tickets_per_booking=1)
        with self.assertRaises(BasketError):
            self.start([(self.seat_1, self.adult),
                        (self.seat_2, self.adult)])
        self.assertFalse(Booking.objects.exists())

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


class ConfirmBookingTests(TestCase):
    """Turning a pending booking's holds into sold seats, all at once
    and only once (architecture 4.32, "One confirmation function")."""

    def setUp(self):
        self.screening, (self.seat_1, self.seat_2) = make_screening()
        self.adult = TicketType.objects.get(name='Adult')
        self.student = TicketType.objects.get(name='Student')
        ScreeningPrice.objects.create(screening=self.screening,
                                      ticket_type=self.adult, price_pence=950)
        ScreeningPrice.objects.create(screening=self.screening,
                                      ticket_type=self.student,
                                      price_pence=750)
        self.booking = start_booking(
            self.screening,
            [(self.seat_1, self.adult), (self.seat_2, self.student)],
            0, 'session-a',
        )

    def sold(self):
        return {(s.seat, s.ticket_type, s.price_pence, s.vat_rate_percent)
                for s in SeatBooking.objects.filter(booking=self.booking)}

    def test_holds_become_sold_seats_at_this_screenings_prices(self):
        confirm_booking(self.booking)
        self.assertEqual(self.sold(), {
            (self.seat_1, self.adult, 950, 20),
            (self.seat_2, self.student, 750, 20),
        })
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PAID)
        self.assertFalse(self.booking.holds.exists())

    def test_confirming_records_when_it_was_paid(self):
        self.assertIsNone(self.booking.paid_at)
        before = timezone.now()
        booking = confirm_booking(self.booking)
        self.assertGreaterEqual(booking.paid_at, before)

    def test_confirming_twice_changes_nothing(self):
        paid_at = confirm_booking(self.booking).paid_at
        confirm_booking(self.booking)
        self.assertEqual(len(self.sold()), 2)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.paid_at, paid_at)

    def test_a_lost_seat_saves_nothing(self):
        """Another sale got one of the seats first, so none of this
        booking's seats are sold and it stays pending."""
        SeatBooking.objects.create(
            booking=Booking.objects.create(screening=self.screening),
            screening=self.screening, seat=self.seat_2,
            ticket_type=self.adult, price_pence=950, vat_rate_percent=20,
        )
        with self.assertRaises(SeatsLost):
            confirm_booking(self.booking)
        self.assertEqual(self.sold(), set())
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        self.assertEqual(self.booking.holds.count(), 2)

    def test_a_hold_that_ran_out_and_went_to_someone_else_saves_nothing(self):
        """The expired hold was cleared and the seat held by another
        customer, so the booking has fewer holds than seats."""
        self.booking.holds.filter(seat=self.seat_2).delete()
        with self.assertRaises(SeatsLost):
            confirm_booking(self.booking)
        self.assertEqual(self.sold(), set())


class StartPaymentTests(TestCase):
    """Choosing Pay: a Checkout Session for the total, and the holds
    extended once to cover it (architecture 4.13 step 3, 4.8 step 5)."""

    def setUp(self):
        FakeProvider.reset()
        self.screening, (self.seat_1, self.seat_2) = make_screening()
        self.adult = TicketType.objects.get(name='Adult')
        self.student = TicketType.objects.get(name='Student')
        for ticket_type, price in ((self.adult, 950), (self.student, 750)):
            ScreeningPrice.objects.create(screening=self.screening,
                                          ticket_type=ticket_type,
                                          price_pence=price)
        self.booking = start_booking(
            self.screening,
            [(self.seat_1, self.adult), (self.seat_2, self.student)],
            0, 'session-a',
        )

    def pay(self):
        return start_payment(self.booking, 'https://site/ok',
                             'https://site/back')

    def test_the_session_is_for_the_total_and_names_the_booking(self):
        session = self.pay()
        asked = FakeProvider.sessions[session.id]
        self.assertEqual(asked['amount_pence'], 1700)
        self.assertEqual(asked['reference'], self.booking.reference)
        self.assertEqual(asked['description'], 'Nosferatu, 2 tickets')

    def test_the_session_is_stored_on_the_booking(self):
        session = self.pay()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.stripe_checkout_session_id, session.id)

    def test_when_the_session_started_is_stored(self):
        """So its age can be asked about when no webhook comes (4.32)."""
        before = timezone.now()
        self.pay()
        self.booking.refresh_from_db()
        self.assertGreaterEqual(self.booking.checkout_started_at, before)
        self.assertLessEqual(self.booking.checkout_started_at,
                             timezone.now())

    def test_returning_to_an_open_session_keeps_its_start(self):
        self.pay()
        self.booking.refresh_from_db()
        started = self.booking.checkout_started_at
        self.pay()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.checkout_started_at, started)

    def test_the_holds_last_as_long_as_the_session(self):
        session = self.pay()
        self.assertEqual(
            set(self.booking.holds.values_list('expires_at', flat=True)),
            {session.expires_at},
        )
        self.assertGreaterEqual(session.expires_at - timezone.now(),
                                timedelta(minutes=30))

    def test_paying_again_returns_the_same_session(self):
        """Pressing Pay twice can't make a second session (4.32), and
        coming back while it's open returns to it (4.13 step 7)."""
        first = self.pay()
        self.booking.refresh_from_db()
        self.assertEqual(self.pay(), first)
        self.assertEqual(len(FakeProvider.sessions), 1)

    def test_paying_after_the_session_expired_gets_a_new_one(self):
        """Otherwise Stripe's idempotency would hand back the expired
        session and the customer could never pay (4.13 step 6)."""
        first = self.pay()
        FakeProvider.expire(first.id)
        self.booking.refresh_from_db()
        second = self.pay()
        self.assertNotEqual(second.id, first.id)
        self.assertTrue(second.is_open)

    def test_a_changed_total_gets_a_new_session(self):
        first = self.pay()
        hold = self.booking.holds.get(seat=self.seat_2)
        hold.ticket_type = self.adult
        hold.save()
        self.booking.refresh_from_db()
        second = self.pay()
        self.assertNotEqual(second.id, first.id)
        self.assertEqual(FakeProvider.sessions[second.id]['amount_pence'],
                         1900)

    def test_seats_whose_hold_ran_out_cant_be_paid_for(self):
        self.booking.holds.update(expires_at=timezone.now())
        with self.assertRaises(HoldsExpired):
            self.pay()
        self.assertEqual(FakeProvider.sessions, {})


class ReleaseSeatsTests(TestCase):
    """A cancelled or refunded booking's seats go back on sale at once,
    and the sold rows stay on record (architecture 4.2, 4.8)."""

    def setUp(self):
        self.screening, (self.seat, _) = make_screening()
        self.adult = TicketType.objects.get(name='Adult')
        ScreeningPrice.objects.create(screening=self.screening,
                                      ticket_type=self.adult, price_pence=950)
        self.booking = confirm_booking(start_booking(
            self.screening, [(self.seat, self.adult)], 0, 'session-a'
        ))

    def test_released_seats_can_be_held_again_and_keep_their_rows(self):
        release_seats(self.booking)
        hold_seats(self.screening, [(self.seat, self.adult)], 'session-b')
        self.assertEqual(self.booking.seats.count(), 1)

    def test_releasing_again_keeps_the_first_time(self):
        release_seats(self.booking)
        released_at = self.booking.seats.get().released_at
        release_seats(self.booking)
        self.assertEqual(self.booking.seats.get().released_at, released_at)


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

    def test_the_seat_count_follows_the_amendment(self):
        self.amend([(self.seat_1, self.adult), (self.seat_2, self.adult),
                    (self.seat_3, self.adult)])
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.seat_count, 3)

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
