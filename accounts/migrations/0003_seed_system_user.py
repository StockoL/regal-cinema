from django.contrib.auth.hashers import make_password
from django.db import migrations

SYSTEM_USER_EMAIL = 'system@regal-cinema.invalid'


def add_system_user(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.get_or_create(email=SYSTEM_USER_EMAIL, defaults={
        'is_active': False,
        # An unusable password: nobody can log in as this account.
        'password': make_password(None),
    })


def remove_system_user(apps, schema_editor):
    apps.get_model('accounts', 'User').objects.filter(
        email=SYSTEM_USER_EMAIL
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_email_verified_at'),
    ]

    operations = [
        migrations.RunPython(add_system_user, remove_system_user),
    ]
