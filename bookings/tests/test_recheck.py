import json

from django.test import TestCase

from bookings.models import Booking, Refund
from bookings.services import recheck_payment, start_booking, start_payment
from bookings.tests.test_holds import make_screening
from bookings.tests.test_webhook import completed
from payments.fake import FakeProvider
from screenings.models import ScreeningPrice, TicketType


class RecheckPaymentTests(TestCase):
    """Asking Stripe about a session when its webhook never came
    (journey 6, "Lost webhook"; architecture 4.32)."""

    def setUp(self):
        FakeProvider.reset()
        screening, (seat, _) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        ScreeningPrice.objects.create(screening=screening, ticket_type=adult,
                                      price_pence=950)
        self.booking = start_booking(screening, [(seat, adult)], 0, 'a')
        self.session = start_payment(self.booking, 'https://site/ok',
                                     'https://site/back')

    def status(self):
        self.booking.refresh_from_db()
        return self.booking.status

    def test_a_paid_session_confirms_its_booking(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        self.assertTrue(recheck_payment(self.booking))
        self.assertEqual(self.status(), Booking.Status.PAID)
        self.assertEqual((self.booking.stripe_payment_intent_id,
                          self.booking.amount_charged_pence), ('pi_1', 950))

    def test_an_unpaid_session_confirms_nothing(self):
        self.assertFalse(recheck_payment(self.booking))
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_a_booking_that_never_reached_stripe_is_left_alone(self):
        self.booking.stripe_checkout_session_id = None
        self.booking.save()
        self.assertFalse(recheck_payment(self.booking))
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_a_late_webhook_confirms_once(self):
        """Named in the testing doc's failure modes (4.32)."""
        FakeProvider.pay(self.session.id, 'pi_1')
        recheck_payment(self.booking)
        payload = json.dumps(completed(self.session.id)).encode()
        self.client.post('/payments/webhook/', payload,
                         content_type='application/json',
                         HTTP_STRIPE_SIGNATURE=FakeProvider.sign(payload))
        self.assertEqual(self.booking.seats.count(), 1)
        self.assertFalse(Refund.objects.exists())

    def test_checking_twice_confirms_once(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        recheck_payment(self.booking)
        recheck_payment(self.booking)
        self.assertEqual(self.booking.seats.count(), 1)
        self.assertFalse(Refund.objects.exists())
