import json

from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking, StripeEvent
from bookings.services import start_booking
from bookings.tests.test_holds import make_screening
from payments.fake import FakeProvider
from screenings.models import ScreeningPrice, TicketType


def completed(session_id, event_id='evt_1', payment_status='paid'):
    return {
        'id': event_id, 'type': 'checkout.session.completed',
        'data': {'object': {
            'id': session_id, 'payment_status': payment_status,
            'payment_intent': 'pi_1', 'amount_total': 950,
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

    def test_a_session_for_something_else_is_acknowledged(self):
        """A membership or gift voucher, once those exist (4.13)."""
        response = self.send(completed('cs_fake_other'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_a_plain_link_does_nothing(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
