from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from bookings.services import confirm_booking, start_booking
from bookings.tests.test_views import make_future_screening
from screenings.models import Screening, ScreeningPrice, Seat, TicketType


class MyBookingsTests(TestCase):
    """Every booking a customer has made, with its status (journey 7,
    "List" and "Detail")."""

    url = reverse('bookings:booking_list')

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.client.force_login(self.user)
        self.adult = TicketType.objects.get(name='Adult')
        self.upcoming = make_future_screening()
        self.past = Screening.objects.create(
            film=self.upcoming.film, screen=self.upcoming.screen,
            layout=self.upcoming.layout,
            ticket_class=self.upcoming.ticket_class,
            date_time=timezone.now() - timedelta(days=7),
        )

    def book(self, screening, number=1, user=None, paid=True):
        seat = Seat.objects.create(
            screen=screening.screen, layout=screening.layout,
            area=Seat.Area.STALLS, number=number, row_index=0,
            column_index=number,
        )
        ScreeningPrice.objects.get_or_create(
            screening=screening, ticket_type=self.adult,
            defaults={'price_pence': 950},
        )
        booking = start_booking(screening, [(seat, self.adult)], 0, 'a',
                                user=user or self.user)
        if paid:
            booking.amount_charged_pence = 950
            booking.save()
            confirm_booking(booking)
        return booking

    def test_the_address_is_under_account(self):
        self.assertEqual(self.url, '/account/bookings/')

    def test_a_visitor_is_asked_to_log_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}"
                                       f"?next={self.url}")

    def test_each_booking_shows_what_was_bought_and_paid(self):
        booking = self.book(self.upcoming)
        response = self.client.get(self.url)
        for words in ('Nosferatu', 'Screen 1', 'Stalls, seat 1, Adult',
                      f'Reference {booking.reference}', '£9.50 paid',
                      'Confirmed'):
            with self.subTest(words=words):
                self.assertContains(response, words)

    def test_upcoming_and_past_are_shown_apart(self):
        soon = self.book(self.upcoming, number=1)
        before = self.book(self.past, number=2)
        html = self.client.get(self.url).content.decode()
        self.assertLess(html.index('>Upcoming<'), html.index(soon.reference))
        self.assertLess(html.index(soon.reference), html.index('>Past<'))
        self.assertLess(html.index('>Past<'), html.index(before.reference))

    def test_a_cancelled_booking_still_shows_with_its_status(self):
        """Brief decision 6: shown as cancelled, not hidden."""
        booking = self.book(self.upcoming)
        booking.status = Booking.Status.CANCELLED
        booking.save()
        response = self.client.get(self.url)
        self.assertContains(response, booking.reference)
        self.assertContains(response, 'Cancelled')

    def test_an_unpaid_booking_isnt_listed(self):
        booking = self.book(self.upcoming, paid=False)
        self.assertNotContains(self.client.get(self.url), booking.reference)

    def test_someone_elses_booking_isnt_listed(self):
        other = get_user_model().objects.create_user(
            'other@example.com', 'a-long-pw-1'
        )
        booking = self.book(self.upcoming, user=other)
        self.assertNotContains(self.client.get(self.url), booking.reference)

    def test_with_no_bookings_it_says_so(self):
        response = self.client.get(self.url)
        self.assertContains(response, "You haven't booked anything yet")

    def test_more_bookings_make_no_more_queries(self):
        """A fixed number of queries, however many bookings (4.33)."""
        self.book(self.upcoming, number=1)
        self.client.get(self.url)
        with self.assertNumQueries(4):
            self.client.get(self.url)
        self.book(self.upcoming, number=2)
        self.book(self.past, number=3)
        with self.assertNumQueries(4):
            self.client.get(self.url)
