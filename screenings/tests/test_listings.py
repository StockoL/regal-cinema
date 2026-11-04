from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase

from screenings.models import (
    Film,
    Screen,
    Screening,
    SeatingLayout,
    TicketClass,
)

LONDON = ZoneInfo('Europe/London')


class PublicScreeningsTests(TestCase):
    """What the public can see. Journey 1, "Private screenings hidden"
    and "Cancelled screening hidden"; architecture 4.11, 4.19."""

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')
        self.layout = SeatingLayout.objects.create(
            screen=self.screen, name='Rows'
        )
        self.film = Film.objects.create(title='Nosferatu', duration_minutes=90)
        self.ticket_class = TicketClass.objects.create(name='Standard')
        self.start = datetime(2026, 11, 14, 11, 0, tzinfo=LONDON)
        self.slot = 0

    def schedule(self, start=None, **fields):
        # Each one three hours after the last, so none overlap.
        if start is None:
            start = self.start + timedelta(hours=3 * self.slot)
            self.slot += 1
        fields.setdefault('film', self.film)
        return Screening.objects.create(
            screen=self.screen, layout=self.layout,
            ticket_class=self.ticket_class, date_time=start, **fields,
        )

    def test_an_ordinary_screening_is_public(self):
        screening = self.schedule()
        self.assertIn(screening, Screening.objects.public())

    def test_a_private_screening_is_never_public(self):
        screening = self.schedule(is_private=True)
        self.assertNotIn(screening, Screening.objects.public())

    def test_a_cancelled_screening_is_never_public(self):
        screening = self.schedule(cancelled_at=self.start)
        self.assertNotIn(screening, Screening.objects.public())

    def test_a_retired_films_screenings_are_not_public(self):
        retired = Film.objects.create(
            title='Old print', duration_minutes=90, is_active=False
        )
        screening = self.schedule(film=retired)
        self.assertNotIn(screening, Screening.objects.public())

    def test_on_date_keeps_one_day_in_the_venues_time(self):
        """A screening at 00:30 on the 15th belongs to the 15th, though
        it's still the 14th in UTC during British Summer Time."""
        late = self.schedule(datetime(2026, 6, 15, 0, 30, tzinfo=LONDON))
        day = self.schedule(datetime(2026, 6, 14, 19, 0, tzinfo=LONDON))
        self.assertEqual(
            list(Screening.objects.public().on_date(date(2026, 6, 14))),
            [day],
        )
        self.assertEqual(
            list(Screening.objects.public().on_date(date(2026, 6, 15))),
            [late],
        )
