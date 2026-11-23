from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from venue.models import VenueSettings, get_settings


class VenueSettingsAdminTests(TestCase):
    """Staff holding manage_venue_settings edit the one row in the admin
    (architecture 4.23)."""

    def setUp(self):
        get_settings()
        self.url = reverse('admin:venue_venuesettings_change', args=[1])
        self.staff = get_user_model().objects.create_user(
            'manager@example.com', 'a-long-pw-1', is_staff=True,
        )
        self.staff.user_permissions.add(
            Permission.objects.get(codename='manage_venue_settings'),
            Permission.objects.get(codename='view_venuesettings'),
        )
        self.client.force_login(self.staff)

    def form(self, **changes):
        data = {
            field.name: getattr(get_settings(), field.name)
            for field in VenueSettings._meta.fields if field.name != 'id'
        }
        data.update(changes)
        return {k: ('on' if v is True else v) for k, v in data.items()
                if v is not False}

    def test_the_permission_lets_staff_change_a_setting(self):
        response = self.client.post(self.url,
                                    self.form(cancellation_cutoff_hours=48))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_settings().cancellation_cutoff_hours, 48)

    def test_without_the_permission_they_cant(self):
        self.staff.user_permissions.remove(
            Permission.objects.get(codename='manage_venue_settings')
        )
        self.client.post(self.url, self.form(cancellation_cutoff_hours=48))
        self.assertEqual(get_settings().cancellation_cutoff_hours, 24)

    def test_there_is_no_second_row_to_add_or_one_to_delete(self):
        superuser = get_user_model().objects.create_superuser(
            'owner@example.com', 'a-long-pw-1'
        )
        self.client.force_login(superuser)
        self.assertEqual(self.client.get(
            reverse('admin:venue_venuesettings_add')
        ).status_code, 403)
        self.assertEqual(self.client.get(
            reverse('admin:venue_venuesettings_delete', args=[1])
        ).status_code, 403)
