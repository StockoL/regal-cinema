import re
from pathlib import Path

from django.conf import settings as django_settings
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse
from django_looseleaf import tokens

from regal.email_config import email_settings


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


class StylesheetTests(TestCase):
    """LooseLeaf UI first, then this project's own styles in LooseLeaf's
    cascade layers, with colours that keep WCAG AA contrast
    (architecture 4.17, 4.24)."""

    def test_pages_load_looseleaf_then_the_projects_styles(self):
        html = self.client.get('/').content.decode()
        looseleaf = html.index('href="/static/looseleaf/looseleaf.css"')
        project = html.index('href="/static/css/main.css"')
        self.assertLess(looseleaf, project)

    def test_every_import_in_main_css_exists(self):
        imports = re.findall(
            r'@import url\("([^"]+)"\)', read_css('main.css')
        )
        for path in imports:
            with self.subTest(path=path):
                self.assertIsNotNone(finders.find(f'css/{path}'))

    def test_every_import_joins_one_of_looseleafs_layers(self):
        layers = {'reset', 'global', 'compositions', 'blocks', 'motion',
                  'utilities'}
        for layer in re.findall(r'layer\((\w+)\)', read_css('main.css')):
            with self.subTest(layer=layer):
                self.assertIn(layer, layers)

    def test_unstyled_lists_lose_the_browsers_indent(self):
        """LooseLeaf's reset drops the bullets from role="list" but keeps
        the browser's left padding, which indents every card and strip."""
        styles = ''.join(
            read_css(path) for path in re.findall(
                r'@import url\("([^"]+)"\) layer\(global\)',
                read_css('main.css'),
            )
        )
        self.assertIn('ul[role="list"]', styles)
        self.assertIn('padding-inline-start: 0', styles)

    def test_every_token_used_is_defined(self):
        """A misspelt custom property fails silently in the browser."""
        looseleaf = Path(
            finders.find('looseleaf/looseleaf.css')
        ).read_text(encoding='utf-8')
        defined = set(re.findall(r'(--[\w-]+):', looseleaf))
        project = list(Path(finders.find('css')).rglob('*.css'))
        for path in project:
            # A block's own variables, declared with a default.
            defined |= set(re.findall(
                r'(--[\w-]+):', path.read_text(encoding='utf-8')
            ))
        for path in project:
            used = set(re.findall(
                r'var\((--[\w-]+)\)', path.read_text(encoding='utf-8')
            ))
            with self.subTest(file=path.name):
                self.assertEqual(used - defined, set())

    def test_text_colours_meet_wcag_aa_on_the_surface(self):
        for scheme in ('light', 'dark'):
            surface = tokens.get('color.surface', scheme)
            for name in ('color.text', 'color.text-muted', 'color.link'):
                with self.subTest(scheme=scheme, token=name):
                    self.assertGreaterEqual(
                        contrast_ratio(tokens.get(name, scheme), surface),
                        4.5,
                    )


def read_css(path):
    return Path(finders.find(f'css/{path}')).read_text(encoding='utf-8')


def contrast_ratio(first, second):
    """WCAG 2.1 contrast ratio between two #rrggbb colours."""

    def luminance(colour):
        channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted(
        (luminance(first), luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


class EmailSettingsTests(TestCase):
    """Email goes through Gmail only when its app password is set in the
    environment, and prints to the console otherwise, so nothing is sent
    by accident while building or testing."""

    def test_without_a_password_emails_print_to_the_console(self):
        mailer = email_settings({})['MAILERS']['default']
        self.assertEqual(
            mailer['BACKEND'],
            'django.core.mail.backends.console.EmailBackend',
        )

    def test_with_a_password_emails_go_through_gmail(self):
        mailer = email_settings({
            'EMAIL_HOST_USER': 'cinema@example.com',
            'EMAIL_HOST_PASSWORD': 'an-app-password',
        })['MAILERS']['default']
        self.assertEqual(
            mailer['BACKEND'], 'django.core.mail.backends.smtp.EmailBackend'
        )
        self.assertEqual(mailer['OPTIONS'], {
            'host': 'smtp.gmail.com',
            'port': 587,
            'use_tls': True,
            'username': 'cinema@example.com',
            'password': 'an-app-password',
        })

    def test_emails_come_from_the_cinema_by_name(self):
        settings = email_settings({'EMAIL_HOST_USER': 'cinema@example.com'})
        self.assertEqual(
            settings['DEFAULT_FROM_EMAIL'],
            'Regal Cinema <cinema@example.com>',
        )


class DatabaseSettingsTests(TestCase):
    """Neon's free plan suspends the database after a few idle minutes
    and drops open connections. A kept connection must be checked before
    reuse, or the first request after a quiet spell fails with a 500."""

    def test_kept_connections_are_checked_before_reuse(self):
        database = django_settings.DATABASES['default']
        self.assertGreater(database['CONN_MAX_AGE'], 0)
        self.assertTrue(database['CONN_HEALTH_CHECKS'])
