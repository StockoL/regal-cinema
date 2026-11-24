from django.contrib.auth.management import create_permissions
from django.contrib.contenttypes.management import create_contenttypes
from django.db import migrations


def give_manager_deactivate(apps, schema_editor):
    """The Manager group may already exist, made before this permission
    did, and groups are only filled in when first made
    (staff/groups.py). So the permission is made first, since Django
    only makes permissions after migrations, then added to it."""
    app_config = apps.get_app_config('accounts')
    app_config.models_module = True
    create_contenttypes(app_config, apps=apps, verbosity=0)
    create_permissions(app_config, apps=apps, verbosity=0)
    manager = apps.get_model('auth', 'Group').objects.filter(
        name='Manager'
    ).first()
    if manager is not None:
        manager.permissions.add(
            apps.get_model('auth', 'Permission').objects.get(
                content_type__app_label='accounts',
                codename='deactivate_account',
            )
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_deactivate_permission'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(give_manager_deactivate,
                             migrations.RunPython.noop),
    ]
