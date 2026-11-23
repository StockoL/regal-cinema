from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from bookings.models import Booking
from bookings.tests.test_holds import make_screening
from staff.audit import log_action
from staff.models import AuditLogEntry


class AuditLogTests(TestCase):
    """Who did something sensitive and why, written by the action itself
    (architecture 4.9)."""

    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            'staff@example.com', 'a-long-pw-1', is_staff=True,
        )
        screening, _ = make_screening()
        self.booking = Booking.objects.create(screening=screening)

    def test_an_entry_names_who_what_why_and_when(self):
        entry = log_action(self.staff,
                           AuditLogEntry.Action.CANCELLATION_DECLINED,
                           'Screening is nearly sold out',
                           booking=self.booking)
        self.assertEqual(
            (entry.actor, entry.action_type, entry.reason,
             entry.related_booking),
            (self.staff, 'cancellation_declined',
             'Screening is nearly sold out', self.booking),
        )
        self.assertIsNotNone(entry.created_at)

    def test_a_reason_is_required(self):
        for reason in ('', '   '):
            with self.subTest(reason=reason):
                with self.assertRaises(ValueError):
                    log_action(self.staff, AuditLogEntry.Action.REFUND,
                               reason)
        self.assertFalse(AuditLogEntry.objects.exists())

    def test_a_staff_account_with_entries_cant_be_deleted(self):
        """4.21: staff are deactivated, so the log always names them."""
        log_action(self.staff, AuditLogEntry.Action.REFUND, 'Duplicate')
        with self.assertRaises(ProtectedError):
            self.staff.delete()

    def test_a_logged_booking_cant_be_deleted(self):
        log_action(self.staff, AuditLogEntry.Action.REFUND, 'Duplicate',
                   booking=self.booking)
        with self.assertRaises(ProtectedError):
            self.booking.delete()
