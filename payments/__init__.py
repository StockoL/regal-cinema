"""Every payment goes through this package (architecture 4.27). Views
and services ask get_provider() for the provider and never import
Stripe themselves, so the tests can swap in the fake."""

from django.conf import settings
from django.utils.module_loading import import_string


def get_provider():
    return import_string(settings.PAYMENT_PROVIDER)()
