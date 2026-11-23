from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import get_system_user
from bookings.models import Booking, Refund, SeatHold
from bookings.reconcile import (
    recheck_stuck_payments,
    retry_refunds,
    tidy_up,
)
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


class TidyUpTests(TestCase):
    """The scheduled check clears away holds and pending bookings left
    behind, and never a paid booking (architecture 4.32)."""

    def setUp(self):
        self.screening, (self.seat_1, self.seat_2) = make_screening()
        self.adult = TicketType.objects.get(name='Adult')
        self.booking = start_booking(self.screening,
                                     [(self.seat_1, self.adult)], 0, 'a')

    def expired(self, hours):
        self.booking.holds.update(
            expires_at=timezone.now() - timedelta(hours=hours),
        )

    def created(self, booking, days):
        Booking.objects.filter(pk=booking.pk).update(
            created_at=timezone.now() - timedelta(days=days),
        )

    def test_a_hold_expired_over_a_day_ago_is_deleted(self):
        self.expired(hours=25)
        self.assertEqual(tidy_up(), {'holds': 1, 'bookings': 0})
        self.assertFalse(SeatHold.objects.exists())

    def test_a_hold_expired_under_a_day_ago_is_kept(self):
        """Lazy expiry already frees the seat (4.8), so there's no hurry."""
        self.expired(hours=23)
        self.assertEqual(tidy_up(), {'holds': 0, 'bookings': 0})
        self.assertTrue(SeatHold.objects.exists())

    def test_a_pending_booking_over_a_week_old_goes_with_its_holds(self):
        self.created(self.booking, days=8)
        self.assertEqual(tidy_up(), {'holds': 0, 'bookings': 1})
        self.assertFalse(Booking.objects.exists())
        self.assertFalse(SeatHold.objects.exists())

    def test_a_pending_booking_under_a_week_old_is_kept(self):
        self.created(self.booking, days=6)
        tidy_up()
        self.assertTrue(Booking.objects.filter(pk=self.booking.pk).exists())

    def test_a_paid_booking_is_never_deleted(self):
        paid = Booking.objects.create(screening=self.screening,
                                      status=Booking.Status.PAID)
        self.created(paid, days=30)
        tidy_up()
        self.assertTrue(Booking.objects.filter(pk=paid.pk).exists())

    def test_a_pending_booking_with_money_on_record_is_kept(self):
        """A refund row means a payment was taken, so it stays for the
        accounts and the needs-attention page."""
        Refund.objects.create(booking=self.booking, amount_pence=950,
                              stripe_payment_intent_id='pi_1',
                              created_by=get_system_user(),
                              reason='duplicate_payment')
        self.created(self.booking, days=8)
        tidy_up()
        self.assertTrue(Booking.objects.filter(pk=self.booking.pk).exists())

    def test_running_twice_is_harmless(self):
        self.created(self.booking, days=8)
        tidy_up()
        self.assertEqual(tidy_up(), {'holds': 0, 'bookings': 0})

    def test_the_command_reports_what_it_removed(self):
        self.created(self.booking, days=8)
        out = StringIO()
        call_command('reconcile_pending', stdout=out)
        self.assertIn('Removed 0 expired holds and 1 abandoned booking.',
                      out.getvalue())


class RefundRetryTests(TestCase):
    """A refund that failed, or never got sent, is sent again with the
    same idempotency key, so it can't pay out twice (architecture 4.13,
    4.32)."""

    def setUp(self):
        FakeProvider.reset()
        screening, _ = make_screening()
        self.booking = Booking.objects.create(
            screening=screening, status=Booking.Status.REFUNDED,
        )

    def refund(self, status, minutes_ago=10):
        refund = Refund.objects.create(
            booking=self.booking, amount_pence=950, reason='duplicate',
            stripe_payment_intent_id='pi_1', status=status,
            created_by=get_system_user(),
        )
        Refund.objects.filter(pk=refund.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_ago),
        )
        return refund

    def test_a_failed_refund_is_sent_again(self):
        refund = self.refund(Refund.Status.FAILED)
        self.assertEqual(retry_refunds(), {'retried': 1, 'succeeded': 1})
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.SUCCEEDED)
        self.assertEqual(len(FakeProvider.refunds), 1)

    def test_one_that_fails_again_stays_failed(self):
        refund = self.refund(Refund.Status.FAILED)
        FakeProvider.fail_refunds = True
        self.assertEqual(retry_refunds(), {'retried': 1, 'succeeded': 0})
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.FAILED)

    def test_a_pending_refund_left_unsent_is_sent(self):
        self.refund(Refund.Status.PENDING)
        self.assertEqual(retry_refunds()['succeeded'], 1)

    def test_a_pending_refund_just_made_is_left_to_its_own_send(self):
        self.refund(Refund.Status.PENDING, minutes_ago=1)
        self.assertEqual(retry_refunds()['retried'], 0)

    def test_a_refund_that_went_through_is_left_alone(self):
        self.refund(Refund.Status.SUCCEEDED)
        self.assertEqual(retry_refunds()['retried'], 0)
        self.assertEqual(FakeProvider.refunds, {})

    def test_sending_again_never_pays_out_twice(self):
        """Stripe saw the first try, but the answer was lost."""
        refund = self.refund(Refund.Status.PENDING)
        FakeProvider().refund(payment_intent_id='pi_1', amount_pence=950,
                              idempotency_key=f'refund-{refund.pk}')
        retry_refunds()
        self.assertEqual(len(FakeProvider.refunds), 1)

    def test_the_command_reports_the_refunds(self):
        self.refund(Refund.Status.FAILED)
        out = StringIO()
        call_command('reconcile_pending', stdout=out)
        self.assertIn('Retried 1 refund: 1 succeeded.', out.getvalue())
