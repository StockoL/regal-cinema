import re

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from bookings.models import Booking
from bookings.tests.test_holds import make_screening


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

    def test_each_booking_gets_a_reference_to_read_out(self):
        booking = self.book()
        self.assertRegex(booking.reference, r'^RGL-[A-Z2-9]{5}$')
        self.assertIsNone(re.search(r'[01OI]', booking.reference[4:]))

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
