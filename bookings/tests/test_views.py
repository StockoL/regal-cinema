from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import SeatHold
from screenings.models import (
    Film,
    Screen,
    Screening,
    ScreeningClosedArea,
    Seat,
    SeatingLayout,
    TicketClass,
    TicketType,
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


class SeatFormTests(TestCase):
    """The seats as a plain form that works without JavaScript, grouped
    the way a customer would look for them (wireframe 04; journey 2)."""

    def setUp(self):
        self.screening = make_future_screening()
        screen, layout = self.screening.screen, self.screening.layout
        self.stalls = [
            Seat.objects.create(
                screen=screen, layout=layout, area=Seat.Area.STALLS,
                number=n, row_index=0, column_index=n,
            )
            for n in (1, 2)
        ]
        self.circle = Seat.objects.create(
            screen=screen, area=Seat.Area.CIRCLE, row_label='A', number=24,
            row_index=0, column_index=0,
        )
        self.url = reverse('bookings:screening_seats',
                           args=[self.screening.pk])

    def page(self):
        return self.client.get(self.url).content.decode()

    def seat_input(self, seat):
        html = self.page()
        start = html.index(f'value="{seat.pk}"')
        return html[html.rindex('<input', 0, start):html.index('>', start)]

    def test_seats_are_grouped_by_area_and_row(self):
        html = self.page()
        self.assertIn('<legend class="legend">Stalls</legend>', html)
        self.assertIn('<legend class="legend">Circle, row A</legend>', html)
        self.assertLess(html.index('>Stalls<'), html.index('>Circle, row A<'))

    def test_each_seat_is_a_checkbox(self):
        self.assertIn('type="checkbox"', self.seat_input(self.circle))
        self.assertNotIn('disabled', self.seat_input(self.circle))

    def test_a_seat_held_by_someone_else_shows_as_sold(self):
        """4.17: to anyone else a held seat is simply unavailable."""
        SeatHold.objects.create(
            screening=self.screening, seat=self.stalls[0],
            ticket_type=TicketType.objects.get(name='Adult'),
            session_key='someone-else',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.assertIn('disabled', self.seat_input(self.stalls[0]))
        self.assertIn('1, sold', self.page())

    def test_an_expired_hold_leaves_the_seat_free(self):
        SeatHold.objects.create(
            screening=self.screening, seat=self.stalls[0],
            ticket_type=TicketType.objects.get(name='Adult'),
            session_key='someone-else',
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertNotIn('disabled', self.seat_input(self.stalls[0]))

    def test_a_closed_area_shows_as_outside_section(self):
        """Journey 2, "Outside section"."""
        ScreeningClosedArea.objects.create(
            screening=self.screening, area=Seat.Area.CIRCLE
        )
        self.assertIn('disabled', self.seat_input(self.circle))
        self.assertIn('24, outside section', self.page())

    def test_a_seat_out_of_use_isnt_offered(self):
        self.stalls[1].is_active = False
        self.stalls[1].save()
        self.assertNotIn(f'value="{self.stalls[1].pk}"', self.page())

    def test_another_layouts_seats_arent_offered(self):
        tables = SeatingLayout.objects.create(
            screen=self.screening.screen, name='Tables'
        )
        other = Seat.objects.create(
            screen=self.screening.screen, layout=tables,
            area=Seat.Area.STALLS, number=9, row_index=0, column_index=9,
        )
        self.assertNotIn(f'value="{other.pk}"', self.page())

    def test_tables_are_their_own_groups(self):
        for seat in self.stalls:
            seat.table_number = 3
            seat.save()
        self.assertIn('<legend class="legend">Stalls, table 3</legend>',
                      self.page())

    def test_the_page_says_the_circle_is_stairs_only(self):
        """Journey 2, "Accessibility note"."""
        self.assertIn('The circle is reached by stairs only.', self.page())


class ChooseSeatsTests(TestCase):
    """Continuing with the chosen seats. They're kept in the session and
    not held yet: holding needs a ticket type for each (4.8 step 3)."""

    def setUp(self):
        self.screening = make_future_screening()
        self.seats = [
            Seat.objects.create(
                screen=self.screening.screen, layout=self.screening.layout,
                area=Seat.Area.STALLS, number=n, row_index=0, column_index=n,
            )
            for n in (1, 2, 3)
        ]
        self.url = reverse('bookings:screening_seats',
                           args=[self.screening.pk])
        self.tickets_url = reverse('bookings:screening_tickets',
                                   args=[self.screening.pk])

    def choose(self, *seats):
        return self.client.post(self.url,
                                {'seats': [seat.pk for seat in seats]})

    def test_continuing_goes_to_the_ticket_types(self):
        response = self.choose(self.seats[0], self.seats[2])
        self.assertRedirects(response, self.tickets_url)
        page = self.client.get(self.tickets_url)
        self.assertContains(page, 'Stalls, seat 1')
        self.assertContains(page, 'Stalls, seat 3')
        self.assertNotContains(page, 'Stalls, seat 2')

    def test_choosing_doesnt_hold_anything_yet(self):
        self.choose(self.seats[0])
        self.assertFalse(SeatHold.objects.exists())

    def test_choosing_nothing_says_so(self):
        response = self.choose()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose at least one seat.')

    def test_a_seat_from_another_screen_is_ignored(self):
        other = Seat.objects.create(
            screen=Screen.objects.create(name='Screen 2'),
            area=Seat.Area.STALLS, number=9, row_index=0, column_index=0,
        )
        self.choose(self.seats[0], other)
        page = self.client.get(self.tickets_url)
        self.assertEqual([s for s, _ in page.context['seats']],
                         [self.seats[0]])

    def test_going_back_keeps_the_seats_ticked(self):
        """Journey 2, "Amend": going back loses nothing."""
        self.choose(self.seats[1])
        html = self.client.get(self.url).content.decode()
        start = html.index(f'value="{self.seats[1].pk}"')
        self.assertIn('checked', html[start:html.index('>', start)])

    def test_the_tickets_step_needs_seats_first(self):
        self.assertRedirects(self.client.get(self.tickets_url), self.url)
