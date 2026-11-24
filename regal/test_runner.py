import logging

from django.conf import settings
from django.test.runner import DiscoverRunner


class RegalTestRunner(DiscoverRunner):
    """Runs the tests with the fake payment provider, whatever the
    environment says, so the suite never calls Stripe (4.27). Log lines
    below critical are switched off for the run, so the failures that
    tests cause on purpose don't bury the results."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.PAYMENT_PROVIDER = 'payments.fake.FakeProvider'
        logging.disable(logging.ERROR)

    def teardown_test_environment(self, **kwargs):
        logging.disable(logging.NOTSET)
        super().teardown_test_environment(**kwargs)
