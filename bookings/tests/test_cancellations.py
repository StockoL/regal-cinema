from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from bookings.models import Booking, Cancellation
from bookings.services import (
    CancellationNotAllowed,
    cancellation_state,
    request_cancellation,
)
from bookings.tests.test_holds import make_screening
from venue.models import VenueSettings


class CancellationModelTests(TestCase):
    """One row for each cancellation, whoever started it (architecture
    4.2)."""

    def setUp(self):
        screening, _ = make_screening()
        self.booking = Booking.objects.create(screening=screening)

    def cancellation(self, **fields):
        return Cancellation.objects.create(
            booking=self.booking, kind=Cancellation.Kind.CUSTOMER_REQUEST,
            **fields,
        )

    def test_a_new_request_waits_for_a_decision(self):
        cancellation = self.cancellation(reason='Wrong night')
        self.assertEqual(cancellation.status, Cancellation.Status.REQUESTED)
        self.assertEqual((cancellation.outcome, cancellation.fee_pence,
                          cancellation.decision_note), ('', 0, ''))
        self.assertIsNone(cancellation.decided_by)
        self.assertIsNone(cancellation.decided_at)
        self.assertIsNotNone(cancellation.requested_at)

    def test_a_booking_with_a_cancellation_cant_be_deleted(self):
        """4.21: it's part of the booking's record."""
        self.cancellation()
        with self.assertRaises(ProtectedError):
            self.booking.delete()

    def test_the_record_stays_if_the_staff_account_goes(self):
        staff = get_user_model().objects.create_user(
            'staff@example.com', 'a-long-pw-1'
        )
        cancellation = self.cancellation(decided_by=staff)
        staff.delete()
        cancellation.refresh_from_db()
        self.assertIsNone(cancellation.decided_by)


class RequestCancellationTests(TestCase):
    """A customer asking to cancel from My bookings (journey 7;
    architecture 4.22)."""

    def setUp(self):
        self.screening, _ = make_screening()
        self.booking = Booking.objects.create(
            screening=self.screening, status=Booking.Status.PAID,
        )

    def starts_in(self, hours):
        self.screening.date_time = timezone.now() + timedelta(hours=hours)
        self.screening.save()

    def test_outside_the_cutoff_the_request_is_recorded(self):
        """Journey 7, "Request outside cutoff"."""
        self.starts_in(48)
        self.assertEqual(cancellation_state(self.booking), 'open')
        request_cancellation(self.booking, reason='Wrong night')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status,
                         Booking.Status.CANCELLATION_REQUESTED)
        cancellation = self.booking.cancellations.get()
        self.assertEqual(
            (cancellation.kind, cancellation.status, cancellation.reason),
            (Cancellation.Kind.CUSTOMER_REQUEST,
             Cancellation.Status.REQUESTED, 'Wrong night'),
        )

    def test_inside_the_cutoff_its_a_phone_call(self):
        """Journey 7, "Inside cutoff": the venue's default is 24 hours."""
        self.starts_in(23)
        self.assertEqual(cancellation_state(self.booking), 'phone')
        with self.assertRaises(CancellationNotAllowed):
            request_cancellation(self.booking)
        self.assertFalse(self.booking.cancellations.exists())

    def test_the_cutoff_is_the_venues_to_set(self):
        VenueSettings.objects.update(cancellation_cutoff_hours=48)
        self.starts_in(30)
        self.assertEqual(cancellation_state(self.booking), 'phone')

    def test_a_past_booking_offers_nothing(self):
        """Journey 7, "Past or cancelled"."""
        self.starts_in(-2)
        self.assertIsNone(cancellation_state(self.booking))
        with self.assertRaises(CancellationNotAllowed):
            request_cancellation(self.booking)

    def test_a_booking_not_paid_for_offers_nothing(self):
        self.starts_in(48)
        for status in (Booking.Status.PENDING, Booking.Status.CANCELLED,
                       Booking.Status.REFUNDED,
                       Booking.Status.CANCELLATION_REQUESTED):
            with self.subTest(status=status):
                self.booking.status = status
                self.assertIsNone(cancellation_state(self.booking))

    def test_asking_twice_records_one_request(self):
        self.starts_in(48)
        request_cancellation(self.booking)
        with self.assertRaises(CancellationNotAllowed):
            request_cancellation(self.booking)
        self.assertEqual(self.booking.cancellations.count(), 1)
