from django.contrib.auth import get_user_model
from django.test import TestCase

from bookings.models import Booking
from bookings.services import CheckInRefused, check_in
from bookings.tests.test_holds import make_screening
from staff.models import AuditLogEntry


class CheckInTests(TestCase):
    """Letting a party in at the door (journey 14, "Check-in";
    architecture 4.2 and 4.9)."""

    def setUp(self):
        screening, _ = make_screening()
        self.booking = Booking.objects.create(screening=screening,
                                              status=Booking.Status.PAID)
        self.staff = get_user_model().objects.create_user(
            'staff@example.com', 'a-long-pw-1', is_staff=True,
        )

    def test_the_booking_records_who_and_when(self):
        check_in(self.booking, self.staff)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.checked_in_by, self.staff)
        self.assertIsNotNone(self.booking.checked_in_at)

    def test_it_is_logged_without_staff_typing_a_reason(self):
        """4.9: the reason is the status reached."""
        check_in(self.booking, self.staff)
        entry = AuditLogEntry.objects.get()
        self.assertEqual(
            (entry.actor, entry.action_type, entry.related_booking,
             entry.reason),
            (self.staff, AuditLogEntry.Action.CHECKED_IN, self.booking,
             'Checked in'),
        )

    def test_checking_in_twice_is_refused(self):
        check_in(self.booking, self.staff)
        with self.assertRaises(CheckInRefused):
            check_in(self.booking, self.staff)
        self.assertEqual(AuditLogEntry.objects.count(), 1)

    def test_only_a_paid_booking_checks_in(self):
        for status in (Booking.Status.PENDING, Booking.Status.CANCELLED,
                       Booking.Status.REFUNDED):
            with self.subTest(status=status):
                Booking.objects.filter(pk=self.booking.pk).update(
                    status=status
                )
                with self.assertRaises(CheckInRefused):
                    check_in(self.booking, self.staff)
        self.assertFalse(AuditLogEntry.objects.exists())
