import json
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from stripe import WebhookSignature

from payments.base import (
    CheckoutSession,
    FeeUnavailable,
    InvalidSignature,
    PaymentFee,
    PaymentUnavailable,
    RefundFailed,
)
from payments.stripe_provider import StripeProvider


EXPIRES = datetime(2026, 12, 1, 18, 30, tzinfo=timezone.utc)


class TestRunTests(SimpleTestCase):

    def test_the_tests_never_use_stripe(self):
        """The test runner swaps in the fake, so a key in .env can't
        make the suite call Stripe (architecture 4.27)."""
        self.assertEqual(settings.PAYMENT_PROVIDER,
                         'payments.fake.FakeProvider')


@override_settings(STRIPE_SECRET_KEY='sk_test_example')
class StripeProviderTests(SimpleTestCase):
    """What the provider asks Stripe for, checked against a stand-in
    client so no request leaves the machine."""

    def setUp(self):
        patcher = mock.patch('payments.stripe_provider.stripe.StripeClient')
        self.client_class = patcher.start()
        self.addCleanup(patcher.stop)
        self.sessions = self.client_class.return_value.v1.checkout.sessions
        self.sessions.create.return_value = SimpleNamespace(
            id='cs_test_1', url='https://checkout.stripe.com/c/pay/cs_test_1',
            expires_at=int(EXPIRES.timestamp()), amount_total=1900,
            status='open', payment_status='unpaid', payment_intent=None,
        )

    def create(self):
        return StripeProvider().create_checkout_session(
            reference='RGL-ABCDE', amount_pence=1900,
            description='Nosferatu, 2 tickets',
            success_url='https://site/ok', cancel_url='https://site/back',
            expires_at=EXPIRES, idempotency_key='booking-1',
        )

    def test_it_uses_the_secret_key_from_the_settings(self):
        self.create()
        self.client_class.assert_called_once_with('sk_test_example')

    def test_it_refuses_anything_but_a_test_mode_key(self):
        """This project only ever runs Stripe in test mode."""
        for key in ('sk_live_example', 'rk_live_example', ''):
            with self.subTest(key=key), self.settings(STRIPE_SECRET_KEY=key):
                with self.assertRaises(ImproperlyConfigured):
                    StripeProvider()

    def test_it_asks_for_one_line_in_pounds_for_the_total(self):
        self.create()
        params = self.sessions.create.call_args.kwargs['params']
        self.assertEqual(params['mode'], 'payment')
        self.assertEqual(params['client_reference_id'], 'RGL-ABCDE')
        self.assertEqual(params['expires_at'], int(EXPIRES.timestamp()))
        self.assertEqual(params['line_items'], [{
            'quantity': 1,
            'price_data': {
                'currency': 'gbp', 'unit_amount': 1900,
                'product_data': {'name': 'Nosferatu, 2 tickets'},
            },
        }])

    def test_it_sends_the_idempotency_key(self):
        self.create()
        options = self.sessions.create.call_args.kwargs['options']
        self.assertEqual(options, {'idempotency_key': 'booking-1'})

    def test_a_session_is_looked_up_with_its_status(self):
        for status, is_open in (('open', True), ('expired', False),
                                ('complete', False)):
            with self.subTest(status=status):
                self.sessions.retrieve.return_value = SimpleNamespace(
                    id='cs_test_1', url='https://checkout.stripe.com/x',
                    expires_at=int(EXPIRES.timestamp()), amount_total=1900,
                    status=status, payment_status='unpaid',
                    payment_intent=None,
                )
                session = StripeProvider().get_checkout_session('cs_test_1')
                self.sessions.retrieve.assert_called_with('cs_test_1')
                self.assertEqual(session.is_open, is_open)

    def test_a_timeout_says_stripe_cant_be_reached(self):
        self.sessions.create.side_effect = stripe.APIConnectionError(
            'Request timed out.'
        )
        with self.assertRaises(PaymentUnavailable):
            self.create()

    def test_a_lookup_that_times_out_says_stripe_cant_be_reached(self):
        self.sessions.retrieve.side_effect = stripe.APIConnectionError(
            'Request timed out.'
        )
        with self.assertRaises(PaymentUnavailable):
            StripeProvider().get_checkout_session('cs_test_1')

    def test_a_paid_session_is_read_with_its_payment(self):
        self.sessions.retrieve.return_value = SimpleNamespace(
            id='cs_test_1', url=None, expires_at=int(EXPIRES.timestamp()),
            amount_total=1900, status='complete', payment_status='paid',
            payment_intent='pi_1',
        )
        session = StripeProvider().get_checkout_session('cs_test_1')
        self.assertEqual((session.paid, session.payment_intent_id),
                         (True, 'pi_1'))

    def test_it_returns_the_session(self):
        self.assertEqual(self.create(), CheckoutSession(
            id='cs_test_1', url='https://checkout.stripe.com/c/pay/cs_test_1',
            expires_at=EXPIRES, amount_pence=1900,
        ))


@override_settings(STRIPE_SECRET_KEY='sk_test_example',
                   STRIPE_WEBHOOK_SECRET='whsec_example')
class StripeWebhookTests(SimpleTestCase):
    """Stripe signs every webhook, and the signature is checked before
    anything in it is trusted (architecture 4.13). Checked with a real
    signature made from a made-up secret, so nothing leaves the
    machine."""

    payload = json.dumps({
        'id': 'evt_1', 'object': 'event', 'type': 'checkout.session.completed',
        'data': {'object': {'id': 'cs_test_1', 'object': 'checkout.session'}},
    })

    def signature(self, secret='whsec_example'):
        now = int(time.time())
        digest = WebhookSignature._compute_signature(
            f'{now}.{self.payload}', secret
        )
        return f't={now},v1={digest}'

    def test_a_signed_event_is_read(self):
        event = StripeProvider().parse_webhook(self.payload,
                                               self.signature())
        self.assertEqual((event.id, event.type, event.object['id']),
                         ('evt_1', 'checkout.session.completed', 'cs_test_1'))

    def test_an_event_signed_with_another_secret_is_refused(self):
        with self.assertRaises(InvalidSignature):
            StripeProvider().parse_webhook(
                self.payload, self.signature('whsec_someone_else')
            )


@override_settings(STRIPE_SECRET_KEY='sk_test_example')
class StripeRefundTests(SimpleTestCase):
    """Refunds against a stand-in client, so nothing leaves the
    machine."""

    def setUp(self):
        patcher = mock.patch('payments.stripe_provider.stripe.StripeClient')
        self.refunds = patcher.start().return_value.v1.refunds
        self.addCleanup(patcher.stop)
        self.refunds.create.return_value = SimpleNamespace(id='re_1')

    def refund(self):
        return StripeProvider().refund(payment_intent_id='pi_1',
                                       amount_pence=950,
                                       idempotency_key='refund-1')

    def test_it_refunds_the_amount_against_the_payment(self):
        self.assertEqual(self.refund(), 're_1')
        self.refunds.create.assert_called_once_with(
            params={'payment_intent': 'pi_1', 'amount': 950},
            options={'idempotency_key': 'refund-1'},
        )

    def test_stripes_error_is_kept_as_the_reason(self):
        self.refunds.create.side_effect = stripe.InvalidRequestError(
            'Charge has already been refunded.', param=None,
        )
        with self.assertRaises(RefundFailed) as caught:
            self.refund()
        self.assertIn('already been refunded', str(caught.exception))


@override_settings(STRIPE_SECRET_KEY='sk_test_example')
class StripeFeeTests(SimpleTestCase):
    """The fee comes from the payment's balance transaction (4.13),
    checked against a stand-in client."""

    def setUp(self):
        patcher = mock.patch('payments.stripe_provider.stripe.StripeClient')
        self.intents = patcher.start().return_value.v1.payment_intents
        self.addCleanup(patcher.stop)

    def charge(self, balance_transaction):
        self.intents.retrieve.return_value = SimpleNamespace(
            latest_charge=SimpleNamespace(
                balance_transaction=balance_transaction,
            ),
        )

    def test_the_fee_and_net_come_from_the_balance_transaction(self):
        self.charge(SimpleNamespace(fee=34, net=916))
        self.assertEqual(StripeProvider().payment_fee('pi_1'),
                         PaymentFee(fee_pence=34, net_pence=916))
        self.intents.retrieve.assert_called_once_with(
            'pi_1',
            params={'expand': ['latest_charge.balance_transaction']},
        )

    def test_a_payment_not_yet_settled_has_no_fee_yet(self):
        self.charge(None)
        with self.assertRaises(FeeUnavailable):
            StripeProvider().payment_fee('pi_1')

    def test_a_stripe_error_means_no_fee_yet(self):
        self.intents.retrieve.side_effect = stripe.APIConnectionError(
            'No connection.'
        )
        with self.assertRaises(FeeUnavailable):
            StripeProvider().payment_fee('pi_1')
