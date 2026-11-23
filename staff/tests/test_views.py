from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class StaffAreaTests(TestCase):
    """The staff area has its own path and login page, apart from the
    customer site (architecture 4.9)."""

    url = reverse('staff:home')
    login = reverse('staff:login')

    def staff(self, group='FrontOfHouse'):
        user = User.objects.create_user('staff@example.com', 'a-long-pw-1',
                                        is_staff=True)
        user.groups.add(Group.objects.get(name=group))
        return user

    def test_the_addresses_are_under_staff(self):
        self.assertEqual((self.url, self.login), ('/staff/', '/staff/login/'))

    def test_a_visitor_is_sent_to_the_staff_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{self.login}?next={self.url}')

    def test_a_customer_is_refused(self):
        self.client.force_login(
            User.objects.create_user('customer@example.com', 'a-long-pw-1')
        )
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_staff_log_in_on_their_own_page_and_land_in_the_staff_area(self):
        self.staff()
        page = self.client.get(self.login)
        self.assertContains(page, 'Staff log in')
        response = self.client.post(self.login, {
            'username': 'staff@example.com', 'password': 'a-long-pw-1',
        })
        self.assertRedirects(response, self.url)

    def test_a_customer_cant_log_in_on_the_staff_page(self):
        User.objects.create_user('customer@example.com', 'a-long-pw-1')
        response = self.client.post(self.login, {
            'username': 'customer@example.com', 'password': 'a-long-pw-1',
        })
        self.assertContains(response, 'only for staff accounts')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_the_home_page_offers_only_the_tools_staff_may_use(self):
        """Code asks for a permission, never a role (4.9)."""
        self.client.force_login(self.staff('FrontOfHouse'))
        self.assertNotContains(self.client.get(self.url), 'Venue settings')
        User.objects.all().delete()
        self.client.force_login(self.staff('Manager'))
        self.assertContains(self.client.get(self.url), 'Venue settings')

    def test_no_customer_page_links_to_the_staff_area(self):
        for url in ('/', reverse('accounts:login'),
                    reverse('accounts:register')):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), 'href="/staff/')
