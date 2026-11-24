from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import get_system_user
from accounts.services import (
    NotACustomerAccount,
    deactivate_account,
    reactivate_account,
)
from bookings.models import Booking
from bookings.tests.test_holds import make_screening
from staff.models import AuditLogEntry

User = get_user_model()


class DeactivationTests(TestCase):
    """Staff can stop a customer account logging in, keeping its
    bookings, and undo it, each with a reason in the audit log
    (journey 12, "Deactivate an account"; architecture 4.32)."""

    def setUp(self):
        self.staff = User.objects.create_user('manager@example.com',
                                              'a-long-pw-1', is_staff=True)
        self.customer = User.objects.create_user('jo@example.com',
                                                 'a-long-pw-1')
        screening, _ = make_screening()
        self.booking = Booking.objects.create(
            screening=screening, user=self.customer,
            status=Booking.Status.PAID,
        )

    def entries(self, action):
        return AuditLogEntry.objects.filter(action_type=action)

    def test_a_deactivated_account_cant_log_in(self):
        self.assertTrue(deactivate_account(self.customer, self.staff,
                                           'Repeated chargebacks'))
        self.assertFalse(self.client.login(username='jo@example.com',
                                           password='a-long-pw-1'))

    def test_it_is_signed_out_wherever_it_was_logged_in(self):
        self.client.force_login(self.customer)
        deactivate_account(self.customer, self.staff, 'Repeated chargebacks')
        response = self.client.get(reverse('bookings:booking_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response['Location'])

    def test_its_bookings_stay(self):
        deactivate_account(self.customer, self.staff, 'Repeated chargebacks')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.user, self.customer)

    def test_it_is_logged_with_who_why_and_whose_account(self):
        deactivate_account(self.customer, self.staff, 'Repeated chargebacks')
        entry = self.entries(AuditLogEntry.Action.ACCOUNT_DEACTIVATED).get()
        self.assertEqual(
            (entry.actor, entry.related_user, entry.reason),
            (self.staff, self.customer, 'Repeated chargebacks'),
        )

    def test_a_reason_is_needed(self):
        with self.assertRaises(ValueError):
            deactivate_account(self.customer, self.staff, '  ')
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)

    def test_deactivating_twice_logs_once(self):
        deactivate_account(self.customer, self.staff, 'Repeated chargebacks')
        self.assertFalse(deactivate_account(self.customer, self.staff,
                                            'Again'))
        self.assertEqual(
            self.entries(AuditLogEntry.Action.ACCOUNT_DEACTIVATED).count(), 1,
        )

    def test_reactivating_lets_it_log_in_again_and_is_logged(self):
        deactivate_account(self.customer, self.staff, 'Repeated chargebacks')
        self.assertTrue(reactivate_account(self.customer, self.staff,
                                           'Deactivated the wrong account'))
        self.assertTrue(self.client.login(username='jo@example.com',
                                          password='a-long-pw-1'))
        entry = self.entries(AuditLogEntry.Action.ACCOUNT_REACTIVATED).get()
        self.assertEqual(entry.related_user, self.customer)

    def test_staff_and_system_accounts_are_left_to_the_admin(self):
        for account in (self.staff, get_system_user()):
            with self.subTest(account=account.email):
                with self.assertRaises(NotACustomerAccount):
                    deactivate_account(account, self.staff, 'A reason')
