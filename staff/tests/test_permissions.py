from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from staff.groups import ensure_groups

STAFF_PERMISSIONS = {
    'cancel_booking', 'refund_booking', 'check_in_booking',
    'create_in_venue_booking', 'view_bookings', 'view_attention',
    'manage_screenings', 'cancel_screening', 'manage_films',
    'manage_venue_settings', 'pause_online_sales', 'view_sales_dashboard',
}


def codenames(group_name):
    return set(Group.objects.get(name=group_name).permissions
               .values_list('codename', flat=True))


class StaffPermissionTests(TestCase):
    """Each sensitive action has its own permission, and groups are
    bundles of them (architecture 4.9)."""

    def test_every_staff_permission_exists(self):
        found = set(Permission.objects.filter(codename__in=STAFF_PERMISSIONS)
                    .values_list('codename', flat=True))
        self.assertEqual(found, STAFF_PERMISSIONS)

    def test_front_of_house_starts_with_the_front_of_house_jobs(self):
        self.assertEqual(codenames('FrontOfHouse'), {
            'cancel_booking', 'check_in_booking', 'create_in_venue_booking',
            'view_bookings', 'view_attention', 'pause_online_sales',
        })

    def test_manager_holds_every_staff_permission(self):
        self.assertLessEqual(STAFF_PERMISSIONS, codenames('Manager'))

    def test_manager_can_look_after_vouchers(self):
        """Added by the membership app for venues whose groups already
        existed, and from the start for new ones."""
        self.assertLessEqual({'view_voucher', 'change_voucher'},
                             codenames('Manager'))

    def test_a_venues_changes_to_a_group_are_kept(self):
        """The groups are defaults, not rules: running migrations again
        never undoes what a venue changed in the admin."""
        group = Group.objects.get(name='FrontOfHouse')
        group.permissions.remove(
            Permission.objects.get(codename='cancel_booking')
        )
        ensure_groups()
        self.assertNotIn('cancel_booking', codenames('FrontOfHouse'))
