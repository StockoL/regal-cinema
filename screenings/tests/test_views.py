from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from screenings.models import (
    Film,
    Screen,
    Screening,
    SeatingLayout,
    TicketClass,
)

LONDON = ZoneInfo('Europe/London')


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
        self.assertContains(self.response, 'aria-label="Main"')
        self.assertContains(self.response, '<footer')

    def test_exactly_one_h1(self):
        self.assertEqual(self.response.content.decode().count('<h1'), 1)

    def test_header_is_a_looseleaf_navbar(self):
        """The menu opens without JavaScript on a narrow screen."""
        self.assertContains(self.response, '<header class="navbar">')
        self.assertContains(self.response, 'class="navbar__brand"')
        self.assertContains(self.response, '<details class="navbar__toggle">')

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


class WhatsOnByDateTests(TestCase):
    """The home page lists one day's screenings, grouped by film, with a
    strip of days to choose from. Journey 1, "Date and showtime picker",
    "Access flags" and "Empty date"."""

    def setUp(self):
        self.today = timezone.localdate()
        screen = Screen.objects.create(name='Screen 1')
        self.layout = SeatingLayout.objects.create(screen=screen, name='Rows')
        self.screen = screen
        self.ticket_class = TicketClass.objects.create(name='Standard')
        self.nosferatu = Film.objects.create(
            title='Nosferatu', duration_minutes=100, age_rating='15'
        )
        self.paddington = Film.objects.create(
            title='Paddington', duration_minutes=95, age_rating='PG'
        )

    def schedule(self, film, day, hour, **fields):
        start = datetime.combine(day, time(hour), tzinfo=LONDON)
        return Screening.objects.create(
            film=film, screen=self.screen, layout=self.layout,
            ticket_class=self.ticket_class, date_time=start, **fields,
        )

    def get(self, day=None):
        url = reverse('screenings:screening_list')
        return self.client.get(url, {'date': day.isoformat()} if day else {})

    def test_shows_todays_screenings_by_default(self):
        self.schedule(self.nosferatu, self.today, 20)
        response = self.get()
        self.assertEqual(response.context['day'], self.today)
        self.assertContains(response, 'Nosferatu')

    def test_another_day_shows_only_that_days_screenings(self):
        tomorrow = self.today + timedelta(days=1)
        self.schedule(self.nosferatu, self.today, 20)
        self.schedule(self.paddington, tomorrow, 11)
        response = self.get(tomorrow)
        self.assertContains(response, 'Paddington')
        self.assertNotContains(response, 'Nosferatu')

    def test_screenings_are_grouped_under_their_film(self):
        self.schedule(self.nosferatu, self.today, 14)
        self.schedule(self.nosferatu, self.today, 20)
        self.schedule(self.paddington, self.today, 11)
        listings = self.get().context['listings']
        self.assertEqual(
            [(film.title, len(times)) for film, times in listings],
            [('Paddington', 1), ('Nosferatu', 2)],
        )

    def test_cancelled_and_private_screenings_are_left_out(self):
        self.schedule(self.nosferatu, self.today, 11, is_private=True)
        self.schedule(self.nosferatu, self.today, 20,
                      cancelled_at=timezone.now())
        self.assertNotContains(self.get(), 'Nosferatu')

    def test_each_film_links_to_its_page_on_the_same_day(self):
        tomorrow = self.today + timedelta(days=1)
        self.schedule(self.nosferatu, tomorrow, 20)
        self.assertContains(
            self.get(tomorrow),
            f'href="/films/nosferatu/?date={tomorrow.isoformat()}"',
        )

    def test_runtime_reads_as_hours_and_minutes(self):
        """The same wording as the film page."""
        self.schedule(self.nosferatu, self.today, 20)
        response = self.get()
        self.assertContains(response, '1 hour 40 minutes')
        self.assertNotContains(response, '100 minutes')

    def test_access_flags_show_on_the_time(self):
        self.schedule(self.nosferatu, self.today, 20, has_captions=True,
                      has_audio_description=True)
        response = self.get()
        self.assertContains(response, 'Captioned')
        self.assertContains(response, 'Audio described')

    def test_the_day_strip_offers_a_week_and_marks_the_chosen_day(self):
        response = self.get(self.today + timedelta(days=2))
        self.assertEqual(len(response.context['days']), 7)
        self.assertContains(response, 'aria-current="date"', count=1)

    def test_a_date_outside_the_week_shows_today(self):
        for day in ('2001-01-01', 'not-a-date'):
            with self.subTest(day=day):
                response = self.client.get(
                    reverse('screenings:screening_list'), {'date': day}
                )
                self.assertEqual(response.context['day'], self.today)

    def test_a_day_with_nothing_on_says_so(self):
        self.assertContains(self.get(), 'Nothing is showing on this day.')
