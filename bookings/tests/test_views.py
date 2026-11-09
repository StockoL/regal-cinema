from datetime import timedelta

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


def make_future_screening(**fields):
    screen = Screen.objects.create(name='Screen 1')
    layout = SeatingLayout.objects.create(screen=screen, name='Rows')
    start = timezone.now() + timedelta(days=2)
    return Screening.objects.create(
        film=Film.objects.create(title='Nosferatu', duration_minutes=100,
                                 age_rating='PG'),
        screen=screen, layout=layout,
        ticket_class=TicketClass.objects.create(name='Standard'),
        date_time=fields.pop('date_time', start), **fields,
    )


class ScreeningSeatsPageTests(TestCase):
    """The page for choosing seats at one screening (architecture 4.25;
    journey 2)."""

    def get(self, screening):
        return self.client.get(
            reverse('bookings:screening_seats', args=[screening.pk])
        )

    def test_the_address_uses_the_screening_id(self):
        self.assertEqual(
            reverse('bookings:screening_seats', args=[7]), '/screenings/7/'
        )

    def test_a_public_screening_opens(self):
        response = self.get(make_future_screening())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nosferatu')

    def test_a_private_screening_is_not_found(self):
        """Journey 1, "Private screenings hidden"."""
        response = self.get(make_future_screening(is_private=True))
        self.assertEqual(response.status_code, 404)

    def test_an_unknown_screening_is_not_found(self):
        self.assertEqual(self.client.get('/screenings/999/').status_code, 404)

    def test_an_old_link_to_a_cancelled_screening_says_so(self):
        """Architecture 4.11."""
        response = self.get(
            make_future_screening(cancelled_at=timezone.now())
        )
        self.assertContains(response, 'This screening has been cancelled',
                            status_code=410)
        self.assertContains(response, reverse('screenings:screening_list'),
                            status_code=410)

    def test_online_sales_close_at_the_listed_start(self):
        """Journey 2, "Sales closed"; architecture 4.23."""
        started = make_future_screening(
            date_time=timezone.now() - timedelta(minutes=1)
        )
        response = self.get(started)
        self.assertContains(response, 'Online sales have closed')
        self.assertContains(response, '01632 960 123')
        self.assertNotContains(response, '<form')
