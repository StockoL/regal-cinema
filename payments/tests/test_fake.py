import json
from datetime import datetime, timezone

from django.test import SimpleTestCase, override_settings

from payments import get_provider
from payments.base import InvalidSignature, WebhookEvent
from payments.fake import FakeProvider


EXPIRES = datetime(2026, 12, 1, 18, 30, tzinfo=timezone.utc)


def create(provider, key='booking-1', amount=1900):
    return provider.create_checkout_session(
        reference='RGL-ABCDE', amount_pence=amount,
        description='2 tickets', success_url='https://site/ok',
        cancel_url='https://site/back', expires_at=EXPIRES,
        idempotency_key=key,
    )


@override_settings(PAYMENT_PROVIDER='payments.fake.FakeProvider')
class FakeProviderTests(SimpleTestCase):
    """The fake stands in for Stripe in the tests, so the suite never
    calls it (architecture 4.27)."""

    def setUp(self):
        FakeProvider.reset()
        self.provider = get_provider()

    def test_the_setting_chooses_the_provider(self):
        self.assertIsInstance(self.provider, FakeProvider)

    def test_a_session_has_an_id_a_page_and_an_expiry(self):
        session = create(self.provider)
        self.assertTrue(session.id.startswith('cs_fake_'))
        self.assertTrue(session.url.startswith('https://'))
        self.assertEqual(session.expires_at, EXPIRES)

    def test_the_same_key_returns_the_same_session(self):
        """As Stripe does, so a repeated Pay can't make a second one."""
        first = create(self.provider)
        self.assertEqual(create(self.provider), first)
        self.assertNotEqual(create(self.provider, key='booking-2'), first)

    def test_it_remembers_what_each_session_was_for(self):
        session = create(self.provider, amount=2450)
        self.assertEqual(FakeProvider.sessions[session.id]['amount_pence'],
                         2450)


class FakeWebhookTests(SimpleTestCase):
    """The fake signs and checks webhooks its own way, so the tests can
    send good and bad ones."""

    payload = json.dumps({
        'id': 'evt_1', 'type': 'checkout.session.completed',
        'data': {'object': {'id': 'cs_fake_1'}},
    }).encode()

    def test_a_signed_event_is_read(self):
        event = FakeProvider().parse_webhook(
            self.payload, FakeProvider.sign(self.payload)
        )
        self.assertEqual(event, WebhookEvent(
            id='evt_1', type='checkout.session.completed',
            object={'id': 'cs_fake_1'},
        ))

    def test_a_bad_signature_is_refused(self):
        with self.assertRaises(InvalidSignature):
            FakeProvider().parse_webhook(self.payload, 'forged')
