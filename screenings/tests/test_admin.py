from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from screenings.models import (
    Film,
    Screen,
    Screening,
    Seat,
    TicketClass,
    TicketType,
)


@override_settings(SCREENING_TRAILER_MINUTES=20,
                   SCREENING_TURNAROUND_MINUTES=15)
class ScreeningsAdminTests(TestCase):
    """The admin is for entering data and one-off fixes until the staff
    pages exist (features, permission model)."""

    def setUp(self):
        user = get_user_model().objects.create_superuser(
            email='manager@example.com', password='a-long-password'
        )
        self.client.force_login(user)
        self.film = Film.objects.create(
            title='Nosferatu', duration_minutes=100
        )
        self.screen = Screen.objects.create(name='Screen 1')
        self.ticket_class = TicketClass.objects.create(name='Standard')
        self.adult = TicketType.objects.create(name='Adult')
        self.start = datetime(2026, 11, 14, 19, 0,
                              tzinfo=ZoneInfo('Europe/London'))

    def test_every_list_and_add_page_loads(self):
        for model in ('film', 'screen', 'ticketclass', 'tickettype',
                      'screening'):
            for page in ('changelist', 'add'):
                with self.subTest(model=model, page=page):
                    url = reverse(f'admin:screenings_{model}_{page}')
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_screen_page_edits_its_seats(self):
        Seat.objects.create(screen=self.screen, row_label='A', seat_number=1,
                            area=Seat.Area.STALLS)
        url = reverse('admin:screenings_screen_change', args=[self.screen.pk])
        response = self.client.get(url)
        self.assertContains(response, 'seats-TOTAL_FORMS')

    def test_screening_page_edits_its_prices_and_shows_ends_at(self):
        screening = Screening.objects.create(
            film=self.film, screen=self.screen,
            ticket_class=self.ticket_class, date_time=self.start,
        )
        url = reverse('admin:screenings_screening_change',
                      args=[screening.pk])
        response = self.client.get(url)
        self.assertContains(response, 'prices-TOTAL_FORMS')
        self.assertContains(response, 'Ends at')

    def test_an_overlapping_screening_shows_the_message(self):
        """Bug 1 in the testing docs, through the admin form."""
        Screening.objects.create(
            film=self.film, screen=self.screen,
            ticket_class=self.ticket_class, date_time=self.start,
        )
        clash = self.start + timedelta(minutes=30)
        response = self.client.post(
            reverse('admin:screenings_screening_add'),
            {
                'film': self.film.pk,
                'screen': self.screen.pk,
                'ticket_class': self.ticket_class.pk,
                'date_time_0': clash.strftime('%d/%m/%Y'),
                'date_time_1': clash.strftime('%H:%M'),
                'prices-TOTAL_FORMS': '0',
                'prices-INITIAL_FORMS': '0',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'overlaps another screening')
        self.assertEqual(Screening.objects.count(), 1)

    def test_film_slug_is_made_when_left_blank(self):
        self.client.post(reverse('admin:screenings_film_add'), {
            'title': 'Paddington', 'duration_minutes': '95', 'slug': '',
            'is_active': 'on',
        })
        self.assertTrue(Film.objects.filter(slug='paddington').exists())
