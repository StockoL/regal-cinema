from django.db import IntegrityError
from django.test import TestCase

from bookings.models import StripeEvent


class StripeEventTests(TestCase):
    """Every Stripe event handled is recorded once, so a redelivered
    one is recognised and ignored (architecture 4.2, 4.13)."""

    def test_an_event_is_recorded_with_its_type_and_time(self):
        event = StripeEvent.objects.create(
            event_id='evt_1', event_type='checkout.session.completed',
        )
        self.assertIsNotNone(event.processed_at)

    def test_an_event_can_only_be_recorded_once(self):
        StripeEvent.objects.create(event_id='evt_1', event_type='a')
        with self.assertRaises(IntegrityError):
            StripeEvent.objects.create(event_id='evt_1', event_type='a')
