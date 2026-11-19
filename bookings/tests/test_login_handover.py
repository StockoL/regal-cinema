from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from bookings.models import Booking
from bookings.tests import test_views


@override_settings(SEAT_HOLD_MINUTES=10)
class LoginHandoverTests(TestCase):
    """Held seats survive logging in mid-checkout: Django gives the
    session a new key at login, so the holds move to the account
    (architecture 4.16)."""

    def setUp(self):
        test = test_views.TicketTypesTests('setUp')
        test.client = self.client
        test.setUp()
        test.submit()
        self.booking = Booking.objects.get()
        self.user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )

    def log_in(self):
        self.client.post(reverse('accounts:login'), {
            'username': 'customer@example.com', 'password': 'a-long-pw-1',
        })

    def test_the_booking_and_its_holds_move_to_the_account(self):
        self.log_in()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.user, self.user)
        self.assertEqual(
            set(self.booking.holds.values_list('user', 'session_key')),
            {(self.user.pk, self.client.session.session_key)},
        )

    def test_the_checkout_page_still_shows_the_seats(self):
        self.log_in()
        url = reverse('bookings:booking_checkout',
                      args=[self.booking.reference])
        self.assertContains(self.client.get(url), 'Stalls, seat 1, Adult')

    def test_someone_elses_booking_isnt_taken(self):
        other = Booking.objects.create(screening=self.booking.screening)
        self.log_in()
        other.refresh_from_db()
        self.assertIsNone(other.user)
