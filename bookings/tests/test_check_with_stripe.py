from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from bookings.services import start_booking, start_payment
from bookings.tests.test_holds import make_screening
from payments.fake import FakeProvider
from screenings.models import ScreeningPrice, TicketType
from staff.models import AuditLogEntry

User = get_user_model()


class CheckWithStripeTests(TestCase):
    """Staff ask Stripe about a payment whose webhook never came
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
        self.started(minutes=6)
        self.staff = User.objects.create_user('staff@example.com',
                                              'a-long-pw-1', is_staff=True)
        self.staff.groups.add(Group.objects.get(name='FrontOfHouse'))
        self.client.force_login(self.staff)
        self.url = reverse('bookings_staff:check_with_stripe',
                           args=[self.booking.reference])

    def started(self, minutes):
        Booking.objects.filter(pk=self.booking.pk).update(
            checkout_started_at=timezone.now() - timedelta(minutes=minutes),
        )

    def check(self):
        return self.client.post(self.url, follow=True)

    def status(self):
        self.booking.refresh_from_db()
        return self.booking.status

    def test_the_address(self):
        self.assertEqual(
            self.url,
            f'/staff/bookings/check-with-stripe/{self.booking.reference}/',
        )

    def test_a_paid_session_is_confirmed_and_logged_under_the_staff(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        response = self.check()
        self.assertContains(response, 'was paid, so it is now confirmed')
        self.assertEqual(self.status(), Booking.Status.PAID)
        entry = AuditLogEntry.objects.get(
            action_type=AuditLogEntry.Action.PAYMENT_CONFIRMED,
        )
        self.assertEqual(entry.actor, self.staff)

    def test_an_unpaid_session_says_so(self):
        response = self.check()
        self.assertContains(response, 'has not been paid')
        self.assertRedirects(response, reverse('bookings_staff:attention'))
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_a_session_under_five_minutes_old_isnt_checked(self):
        """The webhook usually arrives within seconds, so it gets the
        first chance."""
        FakeProvider.pay(self.session.id, 'pi_1')
        self.started(minutes=4)
        response = self.check()
        self.assertContains(response, 'less than five minutes ago')
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_a_booking_already_settled_isnt_checked(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            status=Booking.Status.PAID,
        )
        response = self.check()
        self.assertContains(response, 'is not waiting for payment')

    def test_seats_lost_by_then_are_refunded(self):
        FakeProvider.pay(self.session.id, 'pi_1')
        self.booking.holds.all().delete()
        response = self.check()
        self.assertContains(response, 'its seats had gone')
        self.assertEqual(self.status(), Booking.Status.REFUNDED)

    def test_stripe_out_of_reach_says_so_and_changes_nothing(self):
        FakeProvider.fail_checkout = True
        response = self.check()
        self.assertContains(response, 'could not reach Stripe')
        self.assertEqual(self.status(), Booking.Status.PENDING)

    def test_only_a_post_checks(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_it_needs_the_attention_permission(self):
        self.staff.groups.clear()
        self.assertEqual(self.client.post(self.url).status_code, 403)
