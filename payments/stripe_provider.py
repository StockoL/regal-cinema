from datetime import datetime, timezone

import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import (
    CheckoutSession,
    InvalidSignature,
    PaymentProvider,
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
        return CheckoutSession(
            id=session.id, url=session.url,
            expires_at=datetime.fromtimestamp(session.expires_at,
                                              tz=timezone.utc),
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
