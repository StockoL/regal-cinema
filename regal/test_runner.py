from django.conf import settings
from django.test.runner import DiscoverRunner


class RegalTestRunner(DiscoverRunner):
    """Runs the tests with the fake payment provider, whatever the
    environment says, so the suite never calls Stripe (4.27)."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.PAYMENT_PROVIDER = 'payments.fake.FakeProvider'
