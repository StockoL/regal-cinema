from django.apps import AppConfig
from django.db.models.signals import post_migrate


class StaffConfig(AppConfig):
    name = 'staff'

    def ready(self):
        from .groups import ensure_groups
        # After migrations, once Django has made every permission.
        post_migrate.connect(ensure_groups, sender=self)
