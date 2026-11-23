import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import get_system_user

from bookings.models import Booking, Refund
from bookings.services import recheck_payment, start_booking, start_payment
from bookings.tests.test_holds import make_screening
from bookings.tests.test_webhook import completed
from payments.fake import FakeProvider
from screenings.models import ScreeningPrice, TicketType
from staff.models import AuditLogEntry

REASON = 'Found by the staff check.'


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
        self.staff = get_user_model().objects.create_user(
            'staff@example.com', 'a-long-pw-1', is_staff=True,
        )

    def recheck(self):
        return recheck_payment(self.booking, self.staff, REASON)

    def logged(self):
        return AuditLogEntry.objects.filter(
            action_type=AuditLogEntry.Action.PAYMENT_CONFIRMED,
        )

    def status(self):
        self.booking.refresh_from_db()
        return self.booking.status

    def test_a_paid_session_confirms_its_booking(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        self.assertTrue(self.recheck())
        self.assertEqual(self.status(), Booking.Status.PAID)
        self.assertEqual((self.booking.stripe_payment_intent_id,
                          self.booking.amount_charged_pence), ('pi_1', 950))

    def test_a_booking_it_confirms_is_logged_with_who_found_it(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        self.recheck()
        entry = self.logged().get()
        self.assertEqual((entry.actor, entry.related_booking, entry.reason),
                         (self.staff, self.booking, REASON))

    def test_a_booking_the_webhook_confirmed_first_isnt_logged(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        payload = json.dumps(completed(self.session.id)).encode()
        self.client.post('/payments/webhook/', payload,
                         content_type='application/json',
                         HTTP_STRIPE_SIGNATURE=FakeProvider.sign(payload))
        self.assertTrue(self.recheck())
        self.assertFalse(self.logged().exists())

    def test_seats_lost_by_then_are_refunded_and_not_logged_as_confirmed(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        self.booking.holds.all().delete()
        self.recheck()
        self.assertEqual(self.status(), Booking.Status.REFUNDED)
        self.assertEqual(Refund.objects.get().created_by, get_system_user())
        self.assertFalse(self.logged().exists())

    def test_an_unpaid_session_confirms_nothing(self):
        self.assertFalse(self.recheck())
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_a_booking_that_never_reached_stripe_is_left_alone(self):
        self.booking.stripe_checkout_session_id = None
        self.booking.save()
        self.assertFalse(self.recheck())
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_a_late_webhook_confirms_once(self):
        """Named in the testing doc's failure modes (4.32)."""
        FakeProvider.pay(self.session.id, 'pi_1')
        self.recheck()
        payload = json.dumps(completed(self.session.id)).encode()
        self.client.post('/payments/webhook/', payload,
                         content_type='application/json',
                         HTTP_STRIPE_SIGNATURE=FakeProvider.sign(payload))
        self.assertEqual(self.booking.seats.count(), 1)
        self.assertFalse(Refund.objects.exists())

    def test_checking_twice_confirms_once(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        self.recheck()
        self.recheck()
        self.assertEqual(self.booking.seats.count(), 1)
        self.assertFalse(Refund.objects.exists())
        self.assertEqual(self.logged().count(), 1)
