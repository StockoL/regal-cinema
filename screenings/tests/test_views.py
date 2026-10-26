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

    def test_footer_says_the_venue_is_fictional(self):
        self.assertContains(
            self.response,
            'Regal Cinema is a fictional venue created for a course '
            "project. It isn't connected to any real cinema.",
        )

    def test_footer_gives_the_placeholder_phone_number_as_a_link(self):
        """01632 960 123 is in the range Ofcom keeps for drama."""
        self.assertContains(
            self.response, '<a href="tel:+441632960123">01632 960 123</a>'
        )

    def test_page_doesnt_name_the_real_cinemas_town(self):
        """The real Regal is in Evesham. Naming the town beside the
        name would read as if this were that cinema."""
        self.assertNotContains(self.response, 'Evesham')

    def test_title_names_the_page_and_the_cinema(self):
        self.assertContains(
            self.response, "<title>What's on | Regal Cinema</title>"
        )
