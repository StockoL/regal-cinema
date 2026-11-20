from django.apps import AppConfig


class ScreeningsConfig(AppConfig):
    name = 'screenings'

    def ready(self):
        from . import signals  # noqa: F401, clears the cached layouts
