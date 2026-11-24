from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from staff.models import AuditLogEntry
from venue.models import get_settings


class OnlineSalesPageTests(TestCase):
    """Whoever is on shift can pause online sales when something goes
    wrong, and resume them, saying why (journey 12; architecture
    4.23)."""

    url = '/staff/venue/online-sales/'

    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            'staff@example.com', 'a-long-pw-1', is_staff=True,
        )
        self.staff.groups.add(Group.objects.get(name='FrontOfHouse'))
        self.client.force_login(self.staff)

    def send(self, paused, reason='Stripe is down'):
        return self.client.post(self.url, {
            'paused': '1' if paused else '0', 'reason': reason,
        }, follow=True)

    def logged(self):
        return AuditLogEntry.objects.filter(
            action_type=AuditLogEntry.Action.SETTING_CHANGED,
        )

    def test_the_address(self):
        self.assertEqual(reverse('venue_staff:online_sales'), self.url)

    def test_it_needs_the_pause_permission(self):
        self.staff.groups.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_it_says_sales_are_on_and_offers_to_pause(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Online sales are on.')
        self.assertContains(response, 'Pause online sales</button>')

    def test_pausing_pauses_and_logs_who_and_why(self):
        response = self.send(paused=True)
        self.assertRedirects(response, self.url)
        self.assertContains(response, 'Online sales are paused.')
        self.assertContains(response, 'Resume online sales</button>')
        self.assertTrue(get_settings().online_sales_paused)
        entry = self.logged().get()
        self.assertEqual(entry.actor, self.staff)
        self.assertEqual(entry.reason,
                         'Paused online sales: Stripe is down')

    def test_resuming_resumes_and_logs_it(self):
        self.send(paused=True)
        self.send(paused=False, reason='Stripe is back')
        self.assertFalse(get_settings().online_sales_paused)
        self.assertEqual(self.logged().first().reason,
                         'Resumed online sales: Stripe is back')

    def test_a_reason_is_needed(self):
        response = self.send(paused=True, reason='  ')
        self.assertContains(response, 'Say why')
        self.assertFalse(get_settings().online_sales_paused)
        self.assertFalse(self.logged().exists())

    def test_pausing_twice_changes_nothing_the_second_time(self):
        """A double click, or two people at once."""
        self.send(paused=True)
        response = self.send(paused=True, reason='Again')
        self.assertContains(response, 'already paused')
        self.assertEqual(self.logged().count(), 1)

    def test_the_staff_home_links_to_it(self):
        self.assertContains(self.client.get(reverse('staff:home')),
                            f'href="{self.url}"')
