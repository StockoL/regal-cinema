from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django import forms
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase, override_settings

from screenings.models import Film, Screen, Screening, TicketClass

LONDON = ZoneInfo('Europe/London')


@override_settings(SCREENING_TRAILER_MINUTES=20,
                   SCREENING_TURNAROUND_MINUTES=15)
class ScreeningTests(TestCase):
    """Scheduling and the no-overlap rule (architecture 4.1, 4.21)."""

    def setUp(self):
        self.film = Film.objects.create(
            title='Nosferatu', duration_minutes=100
        )
        self.screen = Screen.objects.create(name='Screen 1')
        self.ticket_class = TicketClass.objects.create(name='Standard')
        self.start = datetime(2026, 11, 14, 19, 0, tzinfo=LONDON)

    def schedule(self, start, **fields):
        fields.setdefault('film', self.film)
        fields.setdefault('screen', self.screen)
        fields.setdefault('ticket_class', self.ticket_class)
        return Screening.objects.create(date_time=start, **fields)

    def test_ends_at_adds_trailers_runtime_and_turnaround(self):
        screening = self.schedule(self.start)
        self.assertEqual(
            screening.ends_at, self.start + timedelta(minutes=20 + 100 + 15)
        )

    def test_overlap_on_the_same_screen_is_rejected(self):
        self.schedule(self.start)
        with self.assertRaises(IntegrityError):
            self.schedule(self.start + timedelta(minutes=60))

    def test_overlap_inside_the_turnaround_is_rejected(self):
        """The room is still being cleared five minutes before the end."""
        first = self.schedule(self.start)
        with self.assertRaises(IntegrityError):
            self.schedule(first.ends_at - timedelta(minutes=5))

    def test_starting_exactly_when_the_last_one_ends_is_allowed(self):
        first = self.schedule(self.start)
        self.schedule(first.ends_at)
        self.assertEqual(Screening.objects.count(), 2)

    @override_settings(SCREENING_TRAILER_MINUTES=0,
                       SCREENING_TURNAROUND_MINUTES=0)
    def test_venue_can_set_both_times_to_zero(self):
        self.schedule(self.start)
        self.schedule(self.start + timedelta(minutes=100))
        self.assertEqual(Screening.objects.count(), 2)

    def test_same_time_on_another_screen_is_allowed(self):
        other = Screen.objects.create(name='Screen 2')
        self.schedule(self.start)
        self.schedule(self.start, screen=other)
        self.assertEqual(Screening.objects.count(), 2)

    def test_a_private_screening_still_blocks_its_slot(self):
        """Architecture 4.19, journey 10 "Still blocks overlap"."""
        self.schedule(self.start, is_private=True)
        with self.assertRaises(IntegrityError):
            self.schedule(self.start + timedelta(minutes=30))

    def test_moving_a_screening_into_another_is_rejected(self):
        """Journey 12: enforced on every save, not only on creation."""
        self.schedule(self.start)
        later = self.schedule(self.start + timedelta(hours=4))
        later.date_time = self.start + timedelta(minutes=30)
        with self.assertRaises(IntegrityError):
            later.save()

    def test_moving_a_screening_a_little_doesnt_clash_with_itself(self):
        screening = self.schedule(self.start)
        screening.date_time = self.start + timedelta(minutes=10)
        screening.save()
        self.assertEqual(
            screening.ends_at, self.start + timedelta(minutes=10 + 135)
        )

    def test_overlap_gives_a_clear_validation_message(self):
        """Journey 12 "Overlap rejected": staff forms call full_clean."""
        self.schedule(self.start)
        clash = Screening(
            film=self.film, screen=self.screen,
            ticket_class=self.ticket_class,
            date_time=self.start + timedelta(minutes=30),
        )
        with self.assertRaises(ValidationError) as caught:
            clash.full_clean()
        self.assertIn('overlaps another screening', str(caught.exception))

    def test_a_form_reports_an_overlap_instead_of_crashing(self):
        """ends_at is never on a form, so Django would otherwise skip the
        constraint and the save would fail in the database."""

        class ScreeningForm(forms.ModelForm):
            class Meta:
                model = Screening
                fields = ['film', 'screen', 'ticket_class', 'date_time']

        self.schedule(self.start)
        form = ScreeningForm(data={
            'film': self.film.pk,
            'screen': self.screen.pk,
            'ticket_class': self.ticket_class.pk,
            'date_time': '2026-11-14 19:30',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('overlaps another screening', str(form.errors))

    def test_changing_the_venue_times_leaves_saved_screenings_alone(self):
        screening = self.schedule(self.start)
        with self.settings(SCREENING_TURNAROUND_MINUTES=60):
            screening.refresh_from_db()
        self.assertEqual(
            screening.ends_at, self.start + timedelta(minutes=135)
        )

    def test_a_cancelled_screening_frees_its_slot(self):
        """Architecture 4.11: staff can schedule a replacement."""
        cancelled = self.schedule(self.start)
        cancelled.cancelled_at = self.start - timedelta(days=1)
        cancelled.save()
        self.schedule(self.start)
        self.assertEqual(Screening.objects.count(), 2)

    def test_a_replacement_in_a_cancelled_slot_passes_validation(self):
        cancelled = self.schedule(self.start)
        cancelled.cancelled_at = self.start - timedelta(days=1)
        cancelled.save()
        replacement = Screening(
            film=self.film, screen=self.screen,
            ticket_class=self.ticket_class, date_time=self.start,
        )
        replacement.full_clean()

    def test_cancelling_keeps_the_screening(self):
        """It stays listed, greyed out, so it never just disappears."""
        screening = self.schedule(self.start)
        self.assertFalse(screening.is_cancelled)
        screening.cancelled_at = self.start - timedelta(days=1)
        screening.save()
        screening.refresh_from_db()
        self.assertTrue(screening.is_cancelled)

    def test_defaults(self):
        screening = self.schedule(self.start)
        self.assertIsNone(screening.public_onsale_at)
        self.assertFalse(screening.is_private)
        self.assertFalse(screening.has_captions)
        self.assertFalse(screening.has_audio_description)

    def test_film_screen_and_ticket_class_cant_be_deleted_once_used(self):
        """PROTECT, architecture 4.21. Retire them with is_active."""
        self.schedule(self.start)
        for record in (self.film, self.screen, self.ticket_class):
            with self.subTest(record=record), transaction.atomic():
                with self.assertRaises(ProtectedError):
                    record.delete()

    def test_string_shows_film_local_time_and_screen(self):
        screening = self.schedule(self.start)
        self.assertEqual(
            str(screening), 'Nosferatu, Sat 14 Nov 2026 19:00, Screen 1'
        )
