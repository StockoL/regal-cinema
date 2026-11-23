"""The two staff groups a venue starts with (architecture 4.9).

They're defaults, not rules: a venue changes what each group holds in
the admin. So a group is only filled in when it's first created, and
running migrations again never undoes a venue's changes. A permission
added by a later feature is added to the groups by that feature."""

from django.contrib.auth.models import Group, Permission

FRONT_OF_HOUSE = [
    'view_bookings', 'check_in_booking', 'create_in_venue_booking',
    'cancel_booking', 'view_attention',
]

# A Manager holds every permission in the project's own apps, which
# includes editing their records in the admin.
PROJECT_APPS = [
    'accounts', 'screenings', 'bookings', 'venue', 'staff', 'membership',
]


def ensure_groups(**kwargs):
    front, created = Group.objects.get_or_create(name='FrontOfHouse')
    if created:
        front.permissions.set(
            Permission.objects.filter(codename__in=FRONT_OF_HOUSE)
        )
    manager, created = Group.objects.get_or_create(name='Manager')
    if created:
        manager.permissions.set(
            Permission.objects.filter(content_type__app_label__in=PROJECT_APPS)
        )
