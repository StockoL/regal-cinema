import json

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import get_system_user
from bookings.models import Booking, OutboundEmail, Refund, StripeEvent
from bookings.services import confirm_booking, start_booking
from bookings.tests.test_holds import make_screening
from payments.base import PaymentFee
from payments.fake import FakeProvider
from screenings.models import ScreeningPrice, TicketType


def completed(session_id, event_id='evt_1', payment_status='paid',
              reference=None, payment_intent='pi_1'):
    return {
        'id': event_id, 'type': 'checkout.session.completed',
        'data': {'object': {
            'id': session_id, 'payment_status': payment_status,
            'payment_intent': payment_intent, 'amount_total': 950,
            'client_reference_id': reference,
        }},
    }


class WebhookTests(TestCase):
    """Stripe's webhook is the only thing that marks a booking paid
    (journey 6, "Sent to Stripe"; architecture 4.13 step 5)."""

    url = '/payments/webhook/'

    def setUp(self):
        screening, (seat, _) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        ScreeningPrice.objects.create(screening=screening, ticket_type=adult,
                                      price_pence=950)
        self.booking = start_booking(screening, [(seat, adult)], 0, 'a')
        self.booking.stripe_checkout_session_id = 'cs_fake_1'
        self.booking.save()

    def send(self, event, signature=None):
        payload = json.dumps(event).encode()
        return self.client.post(
            self.url, payload, content_type='application/json',
            HTTP_STRIPE_SIGNATURE=signature or FakeProvider.sign(payload),
        )

    def status(self):
        self.booking.refresh_from_db()
        return self.booking.status

    def test_the_address(self):
        self.assertEqual(reverse('bookings:stripe_webhook'), self.url)

    def test_a_paid_session_confirms_its_booking(self):
        response = self.send(completed('cs_fake_1'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.status(), Booking.Status.PAID)
        self.assertEqual(self.booking.seats.count(), 1)

    def test_the_payment_is_recorded_on_the_booking(self):
        """What a refund needs later: how it was paid and how much."""
        self.send(completed('cs_fake_1'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.stripe_payment_intent_id, 'pi_1')
        self.assertEqual(self.booking.amount_charged_pence, 950)

    def test_each_event_is_recorded(self):
        self.send(completed('cs_fake_1'))
        self.assertTrue(StripeEvent.objects.filter(
            event_id='evt_1', event_type='checkout.session.completed',
        ).exists())

    def test_a_repeated_webhook_changes_nothing(self):
        """Named in the testing doc's failure modes (4.32)."""
        self.send(completed('cs_fake_1'))
        response = self.send(completed('cs_fake_1'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.count(), 1)
        self.assertEqual(self.booking.seats.count(), 1)

    def test_a_forged_webhook_is_refused(self):
        response = self.send(completed('cs_fake_1'), signature='forged')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.status(), Booking.Status.PENDING)
        self.assertFalse(StripeEvent.objects.exists())

    def test_a_session_not_yet_paid_confirms_nothing(self):
        self.send(completed('cs_fake_1', payment_status='unpaid'))
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_a_payment_on_a_replaced_session_still_finds_its_booking(self):
        """The basket changed after Pay, so the booking holds a newer
        session, but the old one was paid. The reference finds it."""
        self.send(completed('cs_fake_old', reference=self.booking.reference))
        self.assertEqual(self.status(), Booking.Status.PAID)

    def test_a_session_for_something_else_is_acknowledged(self):
        """A membership or gift voucher, once those exist (4.13)."""
        response = self.send(completed('cs_fake_other'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_a_session_that_expired_unpaid_books_nothing(self):
        """4.13 step 6: the booking stays pending, and the event is
        recorded so a repeat is ignored."""
        response = self.send({
            'id': 'evt_2', 'type': 'checkout.session.expired',
            'data': {'object': {'id': 'cs_fake_1', 'status': 'expired'}},
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.status(), Booking.Status.PENDING)
        self.assertTrue(StripeEvent.objects.filter(event_id='evt_2').exists())

    def test_a_plain_link_does_nothing(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class LatePaymentTests(TestCase):
    """A payment that lands after the seats were sold to someone else is
    refunded automatically (journey 6, "Payment after seats lost";
    architecture 4.13)."""

    def setUp(self):
        FakeProvider.reset()
        screening, (seat, _) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        ScreeningPrice.objects.create(screening=screening, ticket_type=adult,
                                      price_pence=950)
        self.booking = start_booking(screening, [(seat, adult)], 0, 'a')
        self.booking.stripe_checkout_session_id = 'cs_fake_1'
        self.booking.save()
        # The hold ran out and someone else bought the seat.
        self.booking.holds.all().delete()
        confirm_booking(start_booking(screening, [(seat, adult)], 0, 'b'))

    def send(self):
        payload = json.dumps(completed('cs_fake_1')).encode()
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                WebhookTests.url, payload, content_type='application/json',
                HTTP_STRIPE_SIGNATURE=FakeProvider.sign(payload),
            )

    def test_a_payment_after_the_seats_went_is_refunded(self):
        """Named in the testing doc's failure modes (4.32)."""
        response = self.send()
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.REFUNDED)
        refund = self.booking.refunds.get()
        self.assertEqual(refund.status, Refund.Status.SUCCEEDED)
        self.assertEqual(refund.created_by, get_system_user())
        self.assertEqual(FakeProvider.refunds[refund.stripe_refund_id],
                         {'payment_intent_id': 'pi_1', 'amount_pence': 950})

    def test_the_customer_is_emailed_about_the_refund(self):
        """4.13: told on the page and by email."""
        self.booking.user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.booking.save()
        self.send()
        sent, = mail.outbox
        self.assertEqual(sent.to, ['customer@example.com'])
        self.assertIn('refund', sent.subject.lower())
        self.assertIn('£9.50', sent.body)
        self.assertEqual(self.booking.emails.get().kind,
                         OutboundEmail.Kind.REFUND_ISSUED)

    def test_a_refund_that_fails_is_kept_with_its_reason(self):
        FakeProvider.fail_refunds = True
        self.send()
        refund = self.booking.refunds.get()
        self.assertEqual(refund.status, Refund.Status.FAILED)
        self.assertIn('told to fail', refund.error)


class DuplicatePaymentTests(TestCase):
    """A second payment for a booking already paid is refunded
    automatically (architecture 4.32, "Paying twice")."""

    def setUp(self):
        FakeProvider.reset()
        screening, (seat, _) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        ScreeningPrice.objects.create(screening=screening, ticket_type=adult,
                                      price_pence=950)
        self.booking = start_booking(screening, [(seat, adult)], 0, 'a')
        self.booking.stripe_checkout_session_id = 'cs_fake_1'
        self.booking.save()
        self.send(completed('cs_fake_1'))

    def send(self, event):
        payload = json.dumps(event).encode()
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                WebhookTests.url, payload, content_type='application/json',
                HTTP_STRIPE_SIGNATURE=FakeProvider.sign(payload),
            )

    def test_a_second_payment_is_refunded(self):
        """Named in the testing doc's failure modes (4.32)."""
        response = self.send(completed(
            'cs_fake_old', event_id='evt_2', payment_intent='pi_2',
            reference=self.booking.reference,
        ))
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PAID)
        self.assertEqual(self.booking.stripe_payment_intent_id, 'pi_1')
        self.assertEqual(self.booking.seats.count(), 1)
        refund = self.booking.refunds.get()
        self.assertEqual(
            (refund.reason, refund.stripe_payment_intent_id,
             refund.amount_pence, refund.status),
            ('duplicate_payment', 'pi_2', 950, Refund.Status.SUCCEEDED),
        )
        self.assertEqual(
            FakeProvider.refunds[refund.stripe_refund_id]['payment_intent_id'],
            'pi_2',
        )

    def test_the_same_payment_again_refunds_nothing(self):
        self.send(completed('cs_fake_1', event_id='evt_2'))
        self.assertFalse(self.booking.refunds.exists())


class PaymentFeeTests(TestCase):
    """What Stripe kept is stored on the booking after it's confirmed,
    and a lookup that fails never undoes the booking (architecture
    4.13)."""

    def setUp(self):
        FakeProvider.reset()
        screening, (seat, _) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        ScreeningPrice.objects.create(screening=screening, ticket_type=adult,
                                      price_pence=950)
        self.booking = start_booking(screening, [(seat, adult)], 0, 'a')
        self.booking.stripe_checkout_session_id = 'cs_fake_1'
        self.booking.save()

    def send(self):
        payload = json.dumps(completed('cs_fake_1')).encode()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                WebhookTests.url, payload, content_type='application/json',
                HTTP_STRIPE_SIGNATURE=FakeProvider.sign(payload),
            )
        self.booking.refresh_from_db()
        return response

    def test_the_fee_and_net_are_stored(self):
        FakeProvider.fees['pi_1'] = PaymentFee(fee_pence=34, net_pence=916)
        self.send()
        self.assertEqual(
            (self.booking.stripe_fee_pence, self.booking.stripe_net_pence),
            (34, 916),
        )

    def test_a_failed_lookup_leaves_the_booking_paid(self):
        response = self.send()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.booking.status, Booking.Status.PAID)
        self.assertIsNone(self.booking.stripe_fee_pence)
