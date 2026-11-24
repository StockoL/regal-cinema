from django.contrib.auth.management import create_permissions
from django.contrib.contenttypes.management import create_contenttypes
from django.db import migrations


def give_groups_pause(apps, schema_editor):
    """Both default groups may already exist, made before this
    permission did, and groups are only filled in when first made
    (staff/groups.py). So the permission is made first, since Django
    only makes permissions after migrations, then added to each."""
    app_config = apps.get_app_config('venue')
    app_config.models_module = True
    create_contenttypes(app_config, apps=apps, verbosity=0)
    create_permissions(app_config, apps=apps, verbosity=0)
    pause = apps.get_model('auth', 'Permission').objects.get(
        content_type__app_label='venue', codename='pause_online_sales',
    )
    for group in apps.get_model('auth', 'Group').objects.filter(
        name__in=['FrontOfHouse', 'Manager'],
    ):
        group.permissions.add(pause)


class Migration(migrations.Migration):

    dependencies = [
        ('venue', '0003_pause_permission'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(give_groups_pause, migrations.RunPython.noop),
    ]
