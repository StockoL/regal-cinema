from django.contrib.auth.models import Permission
from django.test import TestCase

STAFF_PERMISSIONS = {
    'cancel_booking', 'refund_booking', 'check_in_booking',
    'create_in_venue_booking', 'view_bookings', 'view_attention',
    'manage_screenings', 'cancel_screening', 'manage_films',
    'manage_venue_settings', 'view_sales_dashboard',
}


class StaffPermissionTests(TestCase):
    """Each sensitive action has its own permission (architecture
    4.9)."""

    def test_every_staff_permission_exists(self):
        found = set(Permission.objects.filter(codename__in=STAFF_PERMISSIONS)
                    .values_list('codename', flat=True))
        self.assertEqual(found, STAFF_PERMISSIONS)
