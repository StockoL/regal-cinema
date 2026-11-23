from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import get_system_user
from bookings.models import Booking
from bookings.reconcile import recheck_stuck_payments
from bookings.services import start_booking, start_payment
from bookings.tests.test_holds import make_screening
from payments.fake import FakeProvider
from screenings.models import ScreeningPrice, TicketType
from staff.models import AuditLogEntry


class StuckPaymentTests(TestCase):
    """The scheduled check asks Stripe about sessions between 10 minutes
    and 24 hours old whose webhook never came (journey 6, "Lost
    webhook"; architecture 4.32)."""

    def setUp(self):
        FakeProvider.reset()
        screening, (seat, _) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        ScreeningPrice.objects.create(screening=screening, ticket_type=adult,
                                      price_pence=950)
        self.booking = start_booking(screening, [(seat, adult)], 0, 'a')
        self.session = start_payment(self.booking, 'https://site/ok',
                                     'https://site/back')
        self.started(minutes=15)

    def started(self, minutes):
        Booking.objects.filter(pk=self.booking.pk).update(
            checkout_started_at=timezone.now() - timedelta(minutes=minutes),
        )

    def status(self):
        self.booking.refresh_from_db()
        return self.booking.status

    def logged(self):
        return AuditLogEntry.objects.filter(
            action_type=AuditLogEntry.Action.PAYMENT_CONFIRMED,
        )

    def test_a_missing_webhook_is_recovered(self):
        """Named in the testing doc's failure modes (4.32)."""
        FakeProvider.pay(self.session.id, 'pi_1')
        recheck_stuck_payments()
        self.assertEqual(self.status(), Booking.Status.PAID)
        self.assertEqual(self.logged().get().actor, get_system_user())

    def test_running_twice_confirms_once(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        recheck_stuck_payments()
        recheck_stuck_payments()
        self.assertEqual(self.booking.seats.count(), 1)
        self.assertEqual(self.logged().count(), 1)

    def test_an_unpaid_session_stays_pending(self):
        self.assertEqual(recheck_stuck_payments(),
                         {'checked': 1, 'paid': 0, 'unreachable': 0})
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_only_sessions_10_minutes_to_24_hours_old_are_checked(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        for minutes in (9, 24 * 60 + 1):
            with self.subTest(minutes=minutes):
                self.started(minutes)
                self.assertEqual(recheck_stuck_payments()['checked'], 0)
                self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_stripe_out_of_reach_is_counted_and_nothing_changes(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        FakeProvider.fail_checkout = True
        self.assertEqual(recheck_stuck_payments(),
                         {'checked': 1, 'paid': 0, 'unreachable': 1})
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_the_command_reports_what_it_found(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        out = StringIO()
        call_command('reconcile_pending', stdout=out)
        self.assertIn('Checked 1 stuck payment: 1 paid, 0 unreachable.',
                      out.getvalue())
