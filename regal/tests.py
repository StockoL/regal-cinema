from django.test import TestCase, override_settings
from django.urls import reverse


class HealthCheckTests(TestCase):
    """The page cron-job.org requests to keep the Render service awake."""

    def test_returns_ok(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_does_not_touch_the_database(self):
        """A database query on every ping would keep Neon's free compute
        running around the clock."""
        with self.assertNumQueries(0):
            self.client.get(reverse('health'))

    def test_rejects_post(self):
        response = self.client.post(reverse('health'))
        self.assertEqual(response.status_code, 405)

    @override_settings(DEBUG=False)
    def test_works_with_debug_off(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
