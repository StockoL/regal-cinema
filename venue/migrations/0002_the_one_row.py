from django.db import migrations


def add_the_row(apps, schema_editor):
    # Every field has its default, so a fresh deployment works before
    # anyone opens the admin (4.23).
    apps.get_model('venue', 'VenueSettings').objects.get_or_create(pk=1)


class Migration(migrations.Migration):

    dependencies = [
        ('venue', '0001_venue_settings'),
    ]

    operations = [
        migrations.RunPython(add_the_row, migrations.RunPython.noop),
    ]
