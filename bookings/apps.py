from django.apps import AppConfig


class BookingsConfig(AppConfig):
    name = 'bookings'

    def ready(self):
        from . import handover  # noqa: F401, connects the login receiver
