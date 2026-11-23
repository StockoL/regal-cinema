import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from bookings.models import REFERENCE_CHARACTERS, Booking, SeatHold
from bookings.tests.test_holds import make_screening
from screenings.models import TicketType


class BookingTests(TestCase):
    """A booking starts as pending when the customer proceeds to
    checkout, and holds everything that isn't a seat (architecture
    4.2)."""

    def setUp(self):
        self.screening, _ = make_screening()

    def book(self, **fields):
        return Booking.objects.create(screening=self.screening, **fields)

    def test_a_new_booking_is_pending_and_online(self):
        booking = self.book()
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.channel, Booking.Channel.ONLINE)
        self.assertEqual(booking.payment_method,
                         Booking.PaymentMethod.CARD_ONLINE)
        self.assertEqual(booking.infant_count, 0)
        self.assertIsNone(booking.user)

    def test_the_stripe_fee_and_net_wait_for_the_payment(self):
        """Filled in once Stripe says what it kept (4.2, 4.13)."""
        booking = self.book()
        self.assertIsNone(booking.stripe_fee_pence)
        self.assertIsNone(booking.stripe_net_pence)

    def test_a_new_booking_isnt_checked_in(self):
        booking = self.book()
        self.assertIsNone(booking.checked_in_at)
        self.assertIsNone(booking.checked_in_by)

    def test_the_check_in_outlives_the_staff_account(self):
        """4.21: SET_NULL, as the sale still stands."""
        staff = get_user_model().objects.create_user(
            'staff@example.com', 'a-long-pw-1', is_staff=True,
        )
        booking = self.book(checked_in_at=timezone.now(),
                            checked_in_by=staff)
        staff.delete()
        booking.refresh_from_db()
        self.assertIsNone(booking.checked_in_by)
        self.assertIsNotNone(booking.checked_in_at)

    def test_a_dispute_is_open_until_it_closes(self):
        """4.2: open while disputed_at is set and dispute_closed_at
        isn't."""
        booking = self.book()
        self.assertFalse(booking.dispute_open)
        booking.disputed_at = timezone.now()
        self.assertTrue(booking.dispute_open)
        booking.dispute_closed_at = timezone.now()
        self.assertFalse(booking.dispute_open)

    def test_each_booking_gets_a_reference_to_read_out(self):
        booking = self.book()
        self.assertRegex(booking.reference, r'^RGL-[A-Z2-9]{5}$')
        self.assertIsNone(re.search(r'[01OIL]', booking.reference[4:]))

    def test_references_leave_out_characters_easily_misheard(self):
        self.assertFalse(set('01OIL') & set(REFERENCE_CHARACTERS))

    def test_two_bookings_can_never_share_a_checkout_session(self):
        """4.13: the webhook finds the booking by its session."""
        self.book(stripe_checkout_session_id='cs_test_1')
        self.book()
        self.book()
        with self.assertRaises(IntegrityError):
            self.book(stripe_checkout_session_id='cs_test_1')

    def test_references_are_unique(self):
        first = self.book()
        with self.assertRaises(IntegrityError):
            self.book(reference=first.reference)

    def test_a_reference_stays_the_same_when_saved_again(self):
        booking = self.book()
        reference = booking.reference
        booking.infant_count = 1
        booking.save()
        self.assertEqual(booking.reference, reference)

    def test_a_screening_with_bookings_cant_be_deleted(self):
        """Booking.screening is PROTECT (4.21)."""
        self.book()
        with self.assertRaises(ProtectedError):
            self.screening.delete()

    def test_deleting_a_customer_keeps_their_booking(self):
        """Booking.user is SET_NULL, for UK GDPR deletion (4.21)."""
        user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        booking = self.book(user=user)
        user.delete()
        booking.refresh_from_db()
        self.assertIsNone(booking.user)


class PendingBookingHoldTests(TestCase):
    """The seats of a pending booking stay as holds linked to it until
    payment is confirmed (architecture 4.2, 4.8)."""

    def setUp(self):
        self.screening, (self.seat, _) = make_screening()
        self.booking = Booking.objects.create(screening=self.screening)
        self.hold = SeatHold.objects.create(
            screening=self.screening, seat=self.seat,
            ticket_type=TicketType.objects.get(name='Adult'),
            session_key='session-a', booking=self.booking,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    def test_a_pending_booking_lists_its_holds(self):
        self.assertEqual(list(self.booking.holds.all()), [self.hold])

    def test_a_hold_can_exist_before_its_booking(self):
        hold = SeatHold.objects.get()
        hold.booking = None
        hold.save()
        self.assertIsNone(SeatHold.objects.get().booking)

    def test_deleting_a_pending_booking_releases_its_holds(self):
        """SeatHold is CASCADE on its pending Booking (4.21)."""
        self.booking.delete()
        self.assertFalse(SeatHold.objects.exists())
