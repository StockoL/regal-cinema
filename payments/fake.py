from .base import CheckoutSession, PaymentProvider


class FakeProvider(PaymentProvider):
    """Stands in for Stripe in the tests. It keeps what it was asked for
    on the class, so a test can check it, and reset() clears it."""

    sessions = {}
    by_key = {}

    @classmethod
    def reset(cls):
        cls.sessions.clear()
        cls.by_key.clear()

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
            'cancel_url': cancel_url,
        }
        self.by_key[idempotency_key] = session
        return session
