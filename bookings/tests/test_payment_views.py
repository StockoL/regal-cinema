from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from bookings.models import Booking
from bookings.services import confirm_booking
from bookings.tests import test_views


@override_settings(SEAT_HOLD_MINUTES=10)
class ConfirmingPageTests(TestCase):
    """Where Stripe sends the customer back to. Coming back confirms
    nothing: only the webhook does (journey 6, "Confirming"; 4.13 step
    4)."""

    def setUp(self):
        test = test_views.TicketTypesTests('setUp')
        test.client = self.client
        test.setUp()
        test.submit()
        self.booking = Booking.objects.get()
        user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.booking.user = user
        self.booking.save()
        self.client.force_login(user)
        self.url = reverse('bookings:booking_confirming',
                           args=[self.booking.reference])

    def test_a_pending_booking_is_still_being_confirmed(self):
        response = self.client.get(self.url)
        self.assertContains(response, "We're confirming your payment")
        self.assertContains(response, f'href="{self.url}"')
        self.assertNotContains(response, 'Booking confirmed')

    def test_a_paid_booking_shows_its_seats(self):
        confirm_booking(self.booking)
        response = self.client.get(self.url)
        self.assertContains(response, 'Booking confirmed')
        self.assertContains(response, self.booking.reference)
        self.assertContains(response, 'Stalls, seat 1, Adult')
        self.assertContains(response, 'Stalls, seat 2, Child')

    def test_another_visitor_cant_see_it(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 404)
