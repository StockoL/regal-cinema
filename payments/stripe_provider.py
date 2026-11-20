from datetime import datetime, timezone

import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import (
    CheckoutSession,
    FeeUnavailable,
    InvalidSignature,
    PaymentFee,
    PaymentProvider,
    RefundFailed,
    WebhookEvent,
)


class StripeProvider(PaymentProvider):
    """Stripe Checkout, Stripe's hosted payment page, in test mode only
    (architecture 4.13). The only file that imports Stripe."""

    def __init__(self):
        key = settings.STRIPE_SECRET_KEY
        if not key.startswith(('sk_test_', 'rk_test_')):
            raise ImproperlyConfigured(
                'STRIPE_SECRET_KEY must be a Stripe test-mode key.'
            )
        self.client = stripe.StripeClient(key)

    def create_checkout_session(self, *, reference, amount_pence,
                                description, success_url, cancel_url,
                                expires_at, idempotency_key):
        session = self.client.v1.checkout.sessions.create(
            params={
                'mode': 'payment',
                'client_reference_id': reference,
                'line_items': [{
                    'quantity': 1,
                    'price_data': {
                        'currency': 'gbp', 'unit_amount': amount_pence,
                        'product_data': {'name': description},
                    },
                }],
                'success_url': success_url,
                'cancel_url': cancel_url,
                'expires_at': int(expires_at.timestamp()),
            },
            options={'idempotency_key': idempotency_key},
        )
        return checkout_session(session)

    def get_checkout_session(self, session_id):
        return checkout_session(
            self.client.v1.checkout.sessions.retrieve(session_id)
        )

    def parse_webhook(self, payload, signature):
        try:
            event = self.client.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except (stripe.SignatureVerificationError, ValueError):
            raise InvalidSignature() from None
        return WebhookEvent(id=event.id, type=event.type,
                            object=event.data.object.to_dict())

    def refund(self, *, payment_intent_id, amount_pence, idempotency_key):
        try:
            refund = self.client.v1.refunds.create(
                params={'payment_intent': payment_intent_id,
                        'amount': amount_pence},
                options={'idempotency_key': idempotency_key},
            )
        except stripe.StripeError as error:
            raise RefundFailed(error.user_message or str(error)) from None
        return refund.id

    def payment_fee(self, payment_intent_id):
        try:
            intent = self.client.v1.payment_intents.retrieve(
                payment_intent_id,
                params={'expand': ['latest_charge.balance_transaction']},
            )
        except stripe.StripeError as error:
            raise FeeUnavailable(str(error)) from None
        charge = intent.latest_charge
        transaction = charge.balance_transaction if charge else None
        if transaction is None or isinstance(transaction, str):
            raise FeeUnavailable('The payment has not settled yet.')
        return PaymentFee(fee_pence=transaction.fee,
                          net_pence=transaction.net)


def checkout_session(session):
    return CheckoutSession(
        id=session.id, url=session.url,
        expires_at=datetime.fromtimestamp(session.expires_at,
                                          tz=timezone.utc),
        amount_pence=session.amount_total,
        is_open=session.status == 'open',
    )
