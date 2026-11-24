import csv
import io

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, SeatBooking
from bookings.services import check_in
from bookings.tests.test_holds import make_screening
from screenings.models import TicketType

User = get_user_model()


class GuestListSetUp(TestCase):
    """A screening, two seats and a Front of House member logged in."""

    def setUp(self):
        self.screening, (self.seat_1, self.seat_2) = make_screening()
        self.url = reverse('bookings_staff:guest_list',
                           args=[self.screening.pk])
        self.staff = User.objects.create_user('staff@example.com',
                                              'a-long-pw-1', is_staff=True)
        self.staff.groups.add(Group.objects.get(name='FrontOfHouse'))
        self.client.force_login(self.staff)

    def book(self, email, seat, ticket='Adult', status=Booking.Status.PAID,
             **fields):
        booking = Booking.objects.create(
            screening=self.screening, status=status,
            user=User.objects.create_user(email, 'a-long-pw-1'), **fields,
        )
        SeatBooking.objects.create(
            booking=booking, screening=self.screening, seat=seat,
            ticket_type=TicketType.objects.get(name=ticket),
            price_pence=950, vat_rate_percent=20,
        )
        return booking


class GuestListTests(GuestListSetUp):
    """Everyone expected at one screening, for the door (journey 14,
    "Guest list"; architecture 4.32; wireframe brief 20)."""

    def test_the_address_is_under_staff_bookings(self):
        self.assertEqual(
            self.url, f'/staff/bookings/screenings/{self.screening.pk}/guests/'
        )

    def test_each_booking_shows_what_the_door_needs(self):
        booking = self.book('jo@example.com', self.seat_2, ticket='Student',
                            infant_count=1)
        response = self.client.get(self.url)
        for words in ('Nosferatu', booking.reference, 'jo@example.com',
                      'Stalls, seat 2, Student',
                      'Bring proof of age or status', '1 under 2',
                      'Not yet'):
            with self.subTest(words=words):
                self.assertContains(response, words)

    def test_a_reference_stays_on_one_line(self):
        """Read out at the door, so it never breaks at its hyphen; the
        table scrolls sideways on a narrow phone instead."""
        booking = self.book('jo@example.com', self.seat_1)
        html = self.client.get(self.url).content.decode()
        self.assertIn(f'<span class="nowrap">{booking.reference}</span>', html)
        self.assertIn('class="table-wrapper"', html)

    def test_a_party_checked_in_shows_when(self):
        booking = self.book('jo@example.com', self.seat_1)
        check_in(booking, self.staff)
        self.assertContains(self.client.get(self.url), 'Checked in at')

    def test_only_bookings_that_will_be_at_the_door_are_listed(self):
        """A request still waiting stands until staff decide (4.22)."""
        paid = self.book('a@example.com', self.seat_1)
        asked = self.book('b@example.com', self.seat_2,
                          status=Booking.Status.CANCELLATION_REQUESTED)
        gone = Booking.objects.create(screening=self.screening,
                                      status=Booking.Status.CANCELLED)
        html = self.client.get(self.url).content.decode()
        self.assertIn(paid.reference, html)
        self.assertIn(asked.reference, html)
        self.assertNotIn(gone.reference, html)

    def test_a_summary_counts_bookings_seats_and_arrivals(self):
        first = self.book('a@example.com', self.seat_1)
        self.book('b@example.com', self.seat_2)
        check_in(first, self.staff)
        self.assertContains(self.client.get(self.url),
                            '2 bookings, 2 seats, 1 checked in')

    def test_it_needs_view_bookings(self):
        self.staff.groups.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_more_bookings_make_no_more_queries(self):
        """One of the eight is the venue settings, for the footer."""
        self.book('a@example.com', self.seat_1)
        self.client.get(self.url)
        with self.assertNumQueries(8):
            self.client.get(self.url)
        self.book('b@example.com', self.seat_2)
        with self.assertNumQueries(8):
            self.client.get(self.url)


class GuestListDownloadTests(GuestListSetUp):
    """The same rows as a file, for when the site is down (4.32)."""

    def setUp(self):
        super().setUp()
        self.download_url = reverse('bookings_staff:guest_list_download',
                                    args=[self.screening.pk])

    def rows(self):
        response = self.client.get(self.download_url)
        return list(csv.reader(io.StringIO(response.content.decode())))

    def test_it_downloads_as_a_named_csv_file(self):
        response = self.client.get(self.download_url)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="guest-list-nosferatu-2026-12-05.csv"',
        )

    def test_it_holds_a_row_for_each_booking(self):
        booking = self.book('jo@example.com', self.seat_2, ticket='Student',
                            infant_count=1)
        header, row = self.rows()
        self.assertEqual(header, ['Reference', 'Customer', 'Seats',
                                  'Under 2s', 'Status', 'Checked in'])
        self.assertEqual(row, [
            booking.reference, 'jo@example.com',
            'Stalls, seat 2, Student. Bring proof of age or status', '1',
            'Paid', '',
        ])

    def test_the_page_links_to_it(self):
        self.assertContains(self.client.get(self.url), self.download_url)

    def test_downloading_needs_view_bookings(self):
        self.staff.groups.clear()
        self.assertEqual(self.client.get(self.download_url).status_code, 403)


class StaffScreeningsTests(GuestListSetUp):
    """The way into each screening's guest list: one day's screenings,
    today by default (4.32)."""

    screenings_url = reverse('bookings_staff:screening_list')

    def day(self):
        return timezone.localdate(self.screening.date_time).isoformat()

    def test_a_days_screenings_link_to_their_guest_lists(self):
        self.book('a@example.com', self.seat_1)
        response = self.client.get(self.screenings_url, {'date': self.day()})
        self.assertContains(response, 'Nosferatu')
        self.assertContains(response, self.url_for_guests())
        self.assertContains(response, '1 booking')

    def url_for_guests(self):
        return reverse('bookings_staff:guest_list',
                       args=[self.screening.pk])

    def test_another_day_leaves_them_out(self):
        response = self.client.get(self.screenings_url,
                                   {'date': '2027-01-01'})
        self.assertNotContains(response, self.url_for_guests())
        self.assertContains(response, 'No screenings on this day')

    def test_a_cancelled_screening_is_shown_and_labelled(self):
        """Staff still see what the public no longer does (4.11)."""
        self.screening.cancelled_at = timezone.now()
        self.screening.save()
        page = self.client.get(self.screenings_url, {'date': self.day()})
        self.assertContains(page,
                            'Cancelled')

    def test_it_needs_view_bookings(self):
        self.staff.groups.clear()
        response = self.client.get(self.screenings_url)
        self.assertEqual(response.status_code, 403)

    def test_the_staff_home_offers_it(self):
        self.assertContains(self.client.get(reverse('staff:home')),
                            self.screenings_url)
