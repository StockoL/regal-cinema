import re
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse
from django_looseleaf import tokens


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
        self.assertTrue(imports)
        for path in imports:
            with self.subTest(path=path):
                self.assertIsNotNone(finders.find(f'css/{path}'))

    def test_every_import_joins_one_of_looseleafs_layers(self):
        layers = {'reset', 'global', 'compositions', 'blocks', 'motion',
                  'utilities'}
        for layer in re.findall(r'layer\((\w+)\)', read_css('main.css')):
            with self.subTest(layer=layer):
                self.assertIn(layer, layers)

    def test_every_token_used_is_defined_by_looseleaf(self):
        """A misspelt custom property fails silently in the browser."""
        looseleaf = Path(
            finders.find('looseleaf/looseleaf.css')
        ).read_text(encoding='utf-8')
        defined = set(re.findall(r'(--[\w-]+):', looseleaf))
        for path in Path(finders.find('css')).rglob('*.css'):
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
