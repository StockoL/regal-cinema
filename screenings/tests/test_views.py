from django.test import TestCase
from django.urls import reverse


class WhatsOnPageTests(TestCase):
    """The home page and the shared layout from base.html (ux design,
    skeleton plane; architecture 4.17)."""

    def setUp(self):
        self.response = self.client.get(reverse('screenings:screening_list'))

    def test_home_is_whats_on(self):
        self.assertEqual(reverse('screenings:screening_list'), '/')
        self.assertEqual(self.response.status_code, 200)
        self.assertTemplateUsed(self.response, 'base.html')

    def test_page_language_is_british_english(self):
        self.assertContains(self.response, '<html lang="en-GB">')

    def test_skip_link_comes_first_and_targets_main(self):
        html = self.response.content.decode()
        body = html[html.index('<body'):]
        start = body.index('<a ')
        first_link = body[start:body.index('>', start)]
        self.assertIn('href="#main"', first_link)
        self.assertContains(self.response, '<main id="main"')

    def test_page_has_landmarks(self):
        self.assertContains(self.response, '<header')
        self.assertContains(self.response, '<nav aria-label="Main">')
        self.assertContains(self.response, '<footer')

    def test_exactly_one_h1(self):
        self.assertEqual(self.response.content.decode().count('<h1'), 1)

    def test_current_page_is_marked_in_the_nav(self):
        self.assertContains(
            self.response, 'href="/" aria-current="page"'
        )

    def test_title_names_the_page_and_the_cinema(self):
        self.assertContains(
            self.response, "<title>What's on | Regal Cinema</title>"
        )
