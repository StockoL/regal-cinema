from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, SeatBooking
from bookings.services import check_in
from bookings.tests.test_holds import make_screening
from screenings.models import TicketType

User = get_user_model()


class CheckInPageTests(TestCase):
    """Finding a booking and letting the party in, on a phone at the
    door (journey 14; wireframe 22)."""

    url = reverse('bookings_staff:check_in')

    def setUp(self):
        screening, (seat_1, seat_2) = make_screening()
        customer = User.objects.create_user('jo@example.com', 'a-long-pw-1')
        self.booking = Booking.objects.create(
            screening=screening, user=customer, status=Booking.Status.PAID,
            infant_count=1,
        )
        for seat, name in ((seat_1, 'Adult'), (seat_2, 'Student')):
            SeatBooking.objects.create(
                booking=self.booking, screening=screening, seat=seat,
                ticket_type=TicketType.objects.get(name=name),
                price_pence=950, vat_rate_percent=20,
            )
        self.staff = User.objects.create_user('staff@example.com',
                                              'a-long-pw-1', is_staff=True)
        self.staff.groups.add(Group.objects.get(name='FrontOfHouse'))
        self.client.force_login(self.staff)
        self.check_in_url = reverse('bookings_staff:check_in_booking',
                                    args=[self.booking.reference])

    def search(self, query):
        return self.client.get(self.url, {'q': query})

    def test_the_address_is_under_staff_bookings(self):
        self.assertEqual(self.url, '/staff/bookings/check-in/')

    def test_a_booking_found_shows_what_the_door_needs(self):
        response = self.search(self.booking.reference.lower())
        for words in ('Nosferatu', 'jo@example.com', self.booking.reference,
                      'Stalls, seat 1', 'Adult', 'Stalls, seat 2',
                      'Bring proof of age or status', '1 under 2',
                      'Check in 2 seats and 1 infant'):
            with self.subTest(words=words):
                self.assertContains(response, words)

    def test_checking_in_says_so_and_stamps_the_booking(self):
        response = self.client.post(self.check_in_url, follow=True)
        self.assertRedirects(response,
                             f'{self.url}?q={self.booking.reference}')
        self.assertContains(response, f'Checked in {self.booking.reference}')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.checked_in_by, self.staff)

    def test_a_party_already_in_shows_who_let_them_in(self):
        check_in(self.booking, self.staff)
        response = self.search(self.booking.reference)
        self.assertContains(response, 'Checked in at')
        self.assertContains(response, 'staff@example.com')
        self.assertNotContains(response, 'Check in 2 seats')
        again = self.client.post(self.check_in_url, follow=True)
        self.assertContains(again, 'already checked in')

    def test_a_cancelled_booking_cant_be_checked_in(self):
        self.booking.status = Booking.Status.CANCELLED
        self.booking.save()
        response = self.search(self.booking.reference)
        self.assertContains(response, 'Cancelled')
        self.assertNotContains(response, 'Check in 2 seats')

    def test_a_disputed_booking_is_flagged(self):
        """4.13: staff see it, and nothing is cancelled."""
        self.booking.disputed_at = timezone.now()
        self.booking.save()
        self.assertContains(self.search(self.booking.reference),
                            "The customer's bank has disputed this payment")
        self.booking.dispute_closed_at = timezone.now()
        self.booking.save()
        self.assertNotContains(self.search(self.booking.reference),
                               'has disputed this payment')

    def test_nothing_found_says_so(self):
        self.assertContains(self.search('RGL-ZZZZZ'), 'Nothing found')

    def test_a_reference_with_a_character_it_never_has_says_so(self):
        """References leave out 0, O, 1, I and L (4.2), so one typed
        with them is wrong, and the page says why it found nothing."""
        for query in ('RGL-0ABCD', 'rgl abc1d', 'ABCLD'):
            with self.subTest(query=query):
                self.assertContains(
                    self.search(query),
                    'Booking references never contain 0, O, 1, I or L.',
                )

    def test_an_email_search_isnt_told_about_references(self):
        """An email address often has an l in it."""
        self.assertNotContains(self.search('lola@example.com'),
                               'never contain')

    def test_looking_up_needs_view_bookings(self):
        self.staff.groups.clear()
        self.assertEqual(self.search('jo').status_code, 403)

    def test_checking_in_needs_its_own_permission(self):
        """A permission, never a role (4.9)."""
        self.staff.groups.clear()
        self.staff.user_permissions.add(
            Permission.objects.get(codename='view_bookings')
        )
        self.assertNotContains(self.search(self.booking.reference),
                               'Check in 2 seats')
        self.assertEqual(self.client.post(self.check_in_url).status_code,
                         403)

    def test_the_staff_home_offers_it(self):
        self.assertContains(self.client.get(reverse('staff:home')), self.url)

    def test_more_bookings_found_make_no_more_queries(self):
        self.search('jo')
        with self.assertNumQueries(6):
            self.search('jo')
        Booking.objects.create(screening=self.booking.screening,
                               user=self.booking.user,
                               status=Booking.Status.PAID)
        with self.assertNumQueries(6):
            self.search('jo')
