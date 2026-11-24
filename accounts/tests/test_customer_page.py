from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking
from bookings.tests.test_holds import make_screening

User = get_user_model()


class CustomerPageTests(TestCase):
    """Staff look a customer up by email and see their account with
    every booking under it (journey 12; architecture 4.32)."""

    url = '/staff/accounts/'

    def setUp(self):
        self.screening, _ = make_screening()
        self.customer = User.objects.create_user('jo@example.com',
                                                 'a-long-pw-1')
        self.paid = Booking.objects.create(
            screening=self.screening, user=self.customer,
            status=Booking.Status.PAID, amount_charged_pence=1900,
        )
        self.staff = User.objects.create_user('staff@example.com',
                                              'a-long-pw-1', is_staff=True)
        self.staff.groups.add(Group.objects.get(name='FrontOfHouse'))
        self.client.force_login(self.staff)

    def find(self, email):
        return self.client.get(self.url, {'email': email})

    def test_the_address(self):
        self.assertEqual(reverse('accounts_staff:customer'), self.url)

    def test_it_needs_the_bookings_permission(self):
        self.staff.groups.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_an_email_finds_the_account_and_its_bookings(self):
        refunded = Booking.objects.create(
            screening=self.screening, user=self.customer,
            status=Booking.Status.REFUNDED,
        )
        response = self.find(' JO@example.com ')
        self.assertContains(response, 'jo@example.com')
        self.assertContains(response, 'Can log in')
        for booking in (self.paid, refunded):
            with self.subTest(status=booking.status):
                self.assertContains(response, booking.reference)
        self.assertContains(response, 'Refunded')
        self.assertContains(response, '£19.00')

    def test_another_customers_bookings_arent_shown(self):
        other = User.objects.create_user('sam@example.com', 'a-long-pw-1')
        theirs = Booking.objects.create(screening=self.screening, user=other,
                                        status=Booking.Status.PAID)
        self.assertNotContains(self.find('jo@example.com'), theirs.reference)

    def test_an_unknown_email_says_so(self):
        self.assertContains(self.find('nobody@example.com'),
                            'No customer account uses that address.')

    def test_a_staff_account_is_left_to_the_admin(self):
        self.assertContains(self.find('staff@example.com'),
                            'a staff account, managed in the admin')

    def test_more_bookings_make_no_more_queries(self):
        self.find('jo@example.com')
        with self.assertNumQueries(7):
            self.find('jo@example.com')
        Booking.objects.create(screening=self.screening, user=self.customer,
                               status=Booking.Status.PAID)
        with self.assertNumQueries(7):
            self.find('jo@example.com')
