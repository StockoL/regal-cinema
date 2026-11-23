from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from bookings.models import Booking, Cancellation
from bookings.tests.test_holds import make_screening


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
