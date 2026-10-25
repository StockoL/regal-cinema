from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from screenings.models import Film


class FilmTests(TestCase):
    """Films in the local catalogue (architecture 4.1, 4.15)."""

    def make_film(self, **fields):
        fields.setdefault('title', 'Nosferatu')
        fields.setdefault('duration_minutes', 132)
        return Film.objects.create(**fields)

    def test_slug_is_made_from_the_title(self):
        film = self.make_film(title='The Grand Budapest Hotel')
        self.assertEqual(film.slug, 'the-grand-budapest-hotel')

    def test_films_sharing_a_title_get_different_slugs(self):
        """Titles aren't unique: remakes, sequels, re-releases."""
        first = self.make_film()
        second = self.make_film()
        self.assertEqual(first.slug, 'nosferatu')
        self.assertEqual(second.slug, 'nosferatu-2')

    def test_slug_stays_the_same_when_the_title_changes(self):
        """A film's page address shouldn't break if a typo is fixed."""
        film = self.make_film(title='Nosferatoo')
        film.title = 'Nosferatu'
        film.save()
        self.assertEqual(film.slug, 'nosferatoo')

    def test_a_given_slug_is_kept(self):
        film = self.make_film(slug='nosferatu-2024')
        self.assertEqual(film.slug, 'nosferatu-2024')

    def test_tmdb_id_is_optional(self):
        """Event cinema and private hire content has no TMDb entry."""
        first = self.make_film(title='NT Live: Hamlet')
        second = self.make_film(title='Q&A Evening')
        self.assertIsNone(first.tmdb_id)
        self.assertIsNone(second.tmdb_id)

    def test_tmdb_id_is_unique_when_set(self):
        self.make_film(tmdb_id=426063)
        with self.assertRaises(IntegrityError):
            self.make_film(tmdb_id=426063)

    def test_age_rating_must_be_a_bbfc_certificate(self):
        film = Film(title='Nosferatu', duration_minutes=132, age_rating='R')
        with self.assertRaises(ValidationError):
            film.full_clean()

    def test_age_rating_can_be_left_blank(self):
        film = Film(title='Q&A Evening', duration_minutes=60)
        film.full_clean()

    def test_duration_must_be_at_least_a_minute(self):
        film = Film(title='Nosferatu', duration_minutes=0)
        with self.assertRaises(ValidationError):
            film.full_clean()

    def test_new_films_are_active(self):
        self.assertTrue(self.make_film().is_active)

    def test_string_is_the_title(self):
        self.assertEqual(str(self.make_film()), 'Nosferatu')
