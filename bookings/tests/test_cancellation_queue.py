from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, Cancellation
from bookings.services import request_cancellation
from bookings.tests.test_holds import make_screening
from membership.models import Voucher

User = get_user_model()


class CancellationQueueTests(TestCase):
    """Staff deciding customers' cancellation requests (journey 7;
    architecture 4.22; wireframe 21)."""

    url = reverse('bookings_staff:cancellation_list')

    def setUp(self):
        screening, _ = make_screening()
        screening.date_time = timezone.now() + timedelta(days=3)
        screening.save()
        customer = User.objects.create_user('customer@example.com',
                                            'a-long-pw-1')
        self.booking = Booking.objects.create(
            screening=screening, user=customer, status=Booking.Status.PAID,
            amount_charged_pence=1850,
        )
        self.request = request_cancellation(self.booking, "I'm ill")
        self.staff = User.objects.create_user('staff@example.com',
                                              'a-long-pw-1', is_staff=True)
        self.staff.groups.add(Group.objects.get(name='FrontOfHouse'))
        self.client.force_login(self.staff)
        self.decline_url = reverse('bookings_staff:cancellation_decline',
                                   args=[self.request.pk])

    def test_the_address_is_under_staff_bookings(self):
        self.assertEqual(self.url, '/staff/bookings/cancellations/')

    def test_a_waiting_request_shows_what_staff_need_to_decide(self):
        response = self.client.get(self.url)
        for words in (self.booking.reference, 'customer@example.com',
                      'Nosferatu', 'ill', 'voucher for £18.50',
                      'Note to customer (needed either way)', 'Decline',
                      'Approve, issue voucher',
                      'class="textarea"'):
            with self.subTest(words=words):
                self.assertContains(response, words)

    def test_declining_returns_the_booking_and_says_so(self):
        response = self.client.post(self.decline_url,
                                    {'note': 'Nearly sold out'}, follow=True)
        self.assertRedirects(response, self.url)
        self.assertContains(response, 'Declined')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PAID)

    def test_approving_issues_the_voucher_and_says_so(self):
        approve_url = reverse('bookings_staff:cancellation_approve',
                              args=[self.request.pk])
        response = self.client.post(approve_url,
                                    {'note': 'Plenty of time to resell'},
                                    follow=True)
        self.assertRedirects(response, self.url)
        voucher = Voucher.objects.get()
        self.assertContains(response, voucher.code)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CANCELLED)

    def test_approving_without_a_note_changes_nothing(self):
        approve_url = reverse('bookings_staff:cancellation_approve',
                              args=[self.request.pk])
        response = self.client.post(approve_url, {'note': ''}, follow=True)
        self.assertContains(response, 'Write a note to the customer')
        self.assertFalse(Voucher.objects.exists())

    def test_a_decided_request_moves_to_recent_decisions(self):
        self.client.post(self.decline_url, {'note': 'Nearly sold out'})
        response = self.client.get(self.url)
        self.assertContains(response, 'Nothing is waiting')
        self.assertContains(response, 'Cancellation declined')
        self.assertContains(response, 'staff@example.com')

    def test_declining_without_a_note_changes_nothing(self):
        response = self.client.post(self.decline_url, {'note': ''},
                                    follow=True)
        self.assertContains(response, 'Write a note to the customer')
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, Cancellation.Status.REQUESTED)

    def test_staff_without_the_permission_are_refused(self):
        """A permission, never a role (4.9)."""
        self.staff.groups.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(
            self.client.post(self.decline_url, {'note': 'No'}).status_code,
            403,
        )

    def test_a_visitor_is_sent_to_the_staff_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response,
                             f"{reverse('staff:login')}?next={self.url}")

    def test_the_staff_home_offers_the_queue(self):
        self.assertContains(self.client.get(reverse('staff:home')),
                            self.url)

    def test_more_requests_make_no_more_queries(self):
        """Eight: the session, the user, their own and their group's
        permissions, the waiting requests, their seats, the venue
        settings and the recent decisions."""
        self.client.get(self.url)
        with self.assertNumQueries(8):
            self.client.get(self.url)
        other = Booking.objects.create(
            screening=self.booking.screening, user=self.booking.user,
            status=Booking.Status.PAID,
        )
        request_cancellation(other)
        with self.assertNumQueries(8):
            self.client.get(self.url)
