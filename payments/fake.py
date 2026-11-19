import hashlib
import json
from dataclasses import replace

from .base import (
    CheckoutSession,
    InvalidSignature,
    PaymentProvider,
    RefundFailed,
    WebhookEvent,
)


class FakeProvider(PaymentProvider):
    """Stands in for Stripe in the tests. It keeps what it was asked for
    on the class, so a test can check it, and reset() clears it."""

    sessions = {}
    by_key = {}
    refunds = {}
    # Set by a test to make every refund fail (4.32).
    fail_refunds = False

    @classmethod
    def reset(cls):
        cls.sessions.clear()
        cls.by_key.clear()
        cls.refunds.clear()
        cls.fail_refunds = False

    def create_checkout_session(self, *, reference, amount_pence,
                                description, success_url, cancel_url,
                                expires_at, idempotency_key):
        if idempotency_key in self.by_key:
            return self.by_key[idempotency_key]
        session_id = f'cs_fake_{len(self.sessions) + 1}'
        session = CheckoutSession(
            id=session_id,
            url=f'https://checkout.example.com/{session_id}',
            expires_at=expires_at,
        )
        self.sessions[session_id] = {
            'reference': reference, 'amount_pence': amount_pence,
            'description': description, 'success_url': success_url,
            'cancel_url': cancel_url, 'session': session,
        }
        self.by_key[idempotency_key] = session
        return session

    def get_checkout_session(self, session_id):
        return self.sessions[session_id]['session']

    @classmethod
    def expire(cls, session_id):
        """What Stripe does when a session runs out unpaid."""
        info = cls.sessions[session_id]
        info['session'] = replace(info['session'], is_open=False)

    @staticmethod
    def sign(payload):
        """The signature the fake accepts for a payload."""
        return 'fake:' + hashlib.sha256(payload).hexdigest()

    def parse_webhook(self, payload, signature):
        if signature != self.sign(payload):
            raise InvalidSignature()
        event = json.loads(payload)
        return WebhookEvent(id=event['id'], type=event['type'],
                            object=event['data']['object'])

    def refund(self, *, payment_intent_id, amount_pence, idempotency_key):
        if self.fail_refunds:
            raise RefundFailed('The fake provider was told to fail.')
        if idempotency_key not in self.by_key:
            refund_id = f're_fake_{len(self.refunds) + 1}'
            self.refunds[refund_id] = {
                'payment_intent_id': payment_intent_id,
                'amount_pence': amount_pence,
            }
            self.by_key[idempotency_key] = refund_id
        return self.by_key[idempotency_key]
