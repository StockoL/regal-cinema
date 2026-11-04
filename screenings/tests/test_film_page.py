from django.test import TestCase
from django.urls import reverse

from screenings.models import Film
from screenings.templatetags.screenings_extras import runtime


class FilmPageTests(TestCase):
    """A film's own page. Journey 1, "Film detail"; architecture 4.25."""

    def setUp(self):
        self.film = Film.objects.create(
            title='Nosferatu', duration_minutes=132, age_rating='15',
            content_advice='Strong bloody images.',
            synopsis='A young estate agent travels to Transylvania.',
        )

    def get(self, film=None):
        film = film or self.film
        return self.client.get(
            reverse('screenings:film_detail', args=[film.slug])
        )

    def test_the_address_uses_the_slug(self):
        self.assertEqual(
            reverse('screenings:film_detail', args=['nosferatu']),
            '/films/nosferatu/',
        )

    def test_shows_the_film(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1>Nosferatu', html=False)
        self.assertContains(response, 'A young estate agent')
        self.assertContains(response, '2 hours 12 minutes')

    def test_shows_the_rating_with_its_advice(self):
        response = self.get()
        self.assertContains(response, 'Rated 15')
        self.assertContains(response, 'Strong bloody images.')

    def test_a_film_with_no_rating_yet_says_so(self):
        film = Film.objects.create(title='Preview', duration_minutes=90)
        self.assertContains(self.get(film), 'Rating to be confirmed')

    def test_an_age_rated_film_asks_for_photo_id(self):
        """Architecture 4.1: age is checked at the door."""
        line = 'Bring photo ID showing your date of birth.'
        for rating, shown in (('U', False), ('PG', False), ('12A', True),
                              ('15', True), ('18', True)):
            with self.subTest(rating=rating):
                film = Film.objects.create(
                    title=f'Film {rating}', duration_minutes=90,
                    age_rating=rating,
                )
                if shown:
                    self.assertContains(self.get(film), line)
                else:
                    self.assertNotContains(self.get(film), line)

    def test_says_whether_under_2s_can_come(self):
        family = Film.objects.create(
            title='Paddington', duration_minutes=95, age_rating='PG'
        )
        self.assertContains(
            self.get(family), 'Under 2s go free and sit on a lap.'
        )
        self.assertContains(
            self.get(), "Under 2s can't come to this film."
        )

    def test_says_the_circle_is_stairs_only(self):
        self.assertContains(
            self.get(),
            'The circle is reached by stairs only. The stalls are '
            'step-free.',
        )

    def test_the_trailer_is_a_link_that_never_autoplays(self):
        self.film.trailer_key = 'abc123'
        self.film.save()
        response = self.get()
        self.assertContains(
            response, 'href="https://www.youtube.com/watch?v=abc123"'
        )
        self.assertContains(response, 'Watch the trailer')
        self.assertNotContains(response, '<iframe')
        self.assertNotContains(response, 'autoplay')

    def test_no_trailer_means_no_trailer_link(self):
        self.assertNotContains(self.get(), 'Watch the trailer')

    def test_the_title_names_the_film(self):
        self.assertContains(
            self.get(), '<title>Nosferatu | Regal Cinema</title>'
        )

    def test_a_retired_film_is_not_found(self):
        self.film.is_active = False
        self.film.save()
        self.assertEqual(self.get().status_code, 404)

    def test_an_unknown_film_is_not_found(self):
        response = self.client.get('/films/no-such-film/')
        self.assertEqual(response.status_code, 404)


class RuntimeFilterTests(TestCase):

    def test_hours_and_minutes_read_naturally(self):
        cases = {
            132: '2 hours 12 minutes',
            95: '1 hour 35 minutes',
            60: '1 hour',
            121: '2 hours 1 minute',
            45: '45 minutes',
        }
        for minutes, text in cases.items():
            with self.subTest(minutes=minutes):
                self.assertEqual(runtime(minutes), text)
