from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from bookings.models import Booking
from bookings.tests.test_holds import make_screening
from membership.models import Voucher
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

    def test_an_entry_can_name_a_voucher_which_is_then_kept(self):
        voucher = Voucher.objects.create(
            initial_value_pence=1850, remaining_value_pence=1850,
            source=Voucher.Source.BOOKING_CANCELLED,
        )
        entry = log_action(self.staff, AuditLogEntry.Action.VOUCHER_ISSUED,
                           'Approved request', voucher=voucher)
        self.assertEqual(entry.related_voucher, voucher)
        with self.assertRaises(ProtectedError):
            voucher.delete()

    def test_an_entry_can_name_a_customer_account(self):
        customer = get_user_model().objects.create_user('jo@example.com',
                                                        'a-long-pw-1')
        entry = log_action(self.staff,
                           AuditLogEntry.Action.ACCOUNT_DEACTIVATED,
                           'Repeated chargebacks', user=customer)
        self.assertEqual(entry.related_user, customer)

    def test_deleting_the_account_keeps_the_entry_without_it(self):
        """A GDPR deletion removes who it was, not what was done (4.21)."""
        customer = get_user_model().objects.create_user('jo@example.com',
                                                        'a-long-pw-1')
        entry = log_action(self.staff,
                           AuditLogEntry.Action.ACCOUNT_DEACTIVATED,
                           'Repeated chargebacks', user=customer)
        customer.delete()
        entry.refresh_from_db()
        self.assertIsNone(entry.related_user)
        self.assertEqual(entry.reason, 'Repeated chargebacks')
