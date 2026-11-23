from django.contrib.auth.management import create_permissions
from django.contrib.contenttypes.management import create_contenttypes
from django.db import migrations


def give_manager_voucher_permissions(apps, schema_editor):
    """A venue's Manager group may already exist, made before vouchers
    did, and groups are only filled in when first made (staff/groups.py).
    So this app adds its own permissions to it, making them first, since
    Django only makes permissions after migrations."""
    app_config = apps.get_app_config('membership')
    app_config.models_module = True
    create_contenttypes(app_config, apps=apps, verbosity=0)
    create_permissions(app_config, apps=apps, verbosity=0)
    manager = apps.get_model('auth', 'Group').objects.filter(
        name='Manager'
    ).first()
    if manager is not None:
        manager.permissions.add(*apps.get_model('auth', 'Permission')
                                .objects.filter(
                                    content_type__app_label='membership'
                                ))


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0001_voucher'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(give_manager_voucher_permissions,
                             migrations.RunPython.noop),
    ]
