from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.test import TestCase

from screenings.models import (
    Film,
    Screen,
    Screening,
    ScreeningPrice,
    Seat,
    SeatingLayout,
    TicketClass,
    TicketType,
)
from screenings.services import fill_prices, layout_seats


class FillPricesTests(TestCase):
    """A new screening's price table starts from its ticket class.
    Journey 12, "Price table"; architecture 4.1."""

    def setUp(self):
        screen = Screen.objects.create(name='Screen 1')
        self.layout = SeatingLayout.objects.create(screen=screen, name='Rows')
        self.screen = screen
        self.standard = TicketClass.objects.create(
            name='Standard', default_price_pence=900
        )

    def screening(self, rating='PG', ticket_class=None):
        return Screening.objects.create(
            film=Film.objects.create(
                title='A film', duration_minutes=90, age_rating=rating
            ),
            screen=self.screen, layout=self.layout,
            ticket_class=ticket_class or self.standard,
            date_time=datetime(2026, 11, 14, 19, 0,
                               tzinfo=ZoneInfo('Europe/London')),
        )

    def prices(self, screening):
        return dict(screening.prices.values_list(
            'ticket_type__name', 'price_pence'
        ))

    def test_each_offered_type_gets_the_class_default(self):
        screening = self.screening()
        fill_prices(screening)
        self.assertEqual(self.prices(screening), {
            'Adult': 900, 'Student': 900, 'OAP': 900, 'Young person': 900,
            'Child': 900, 'Companion': 0,
        })

    def test_types_the_rating_leaves_out_get_no_row(self):
        screening = self.screening(rating='18')
        fill_prices(screening)
        self.assertNotIn('Child', self.prices(screening))
        self.assertNotIn('Young person', self.prices(screening))

    def test_a_price_staff_already_set_is_kept(self):
        screening = self.screening()
        ScreeningPrice.objects.create(
            screening=screening,
            ticket_type=TicketType.objects.get(name='Child'),
            price_pence=650,
        )
        fill_prices(screening)
        self.assertEqual(self.prices(screening)['Child'], 650)

    def test_a_class_with_no_default_only_fills_the_free_ticket(self):
        """Staff type each price in for a class such as Live Event."""
        live = TicketClass.objects.create(name='Live Event')
        screening = self.screening(ticket_class=live)
        fill_prices(screening)
        self.assertEqual(self.prices(screening), {'Companion': 0})


class LayoutSeatsTests(TestCase):
    """A layout's seats are cached, and any change to a seat or layout
    clears the cache (architecture 4.33; brief decision 97)."""

    def setUp(self):
        cache.clear()
        self.screen = Screen.objects.create(name='Screen 1')
        self.layout = SeatingLayout.objects.create(screen=self.screen,
                                                   name='Rows')
        self.stalls = self.seat(number=1, layout=self.layout)
        self.circle = self.seat(number=2, area=Seat.Area.CIRCLE,
                                row_label='A')

    def seat(self, number, layout=None, area=Seat.Area.STALLS, **fields):
        return Seat.objects.create(
            screen=self.screen, layout=layout, area=area, number=number,
            row_index=0, column_index=number, **fields,
        )

    def seats(self):
        return layout_seats(self.screen.pk, self.layout.pk)

    def test_fixed_and_layout_seats_in_use_in_grid_order(self):
        self.seat(number=3, layout=self.layout, is_active=False)
        other = SeatingLayout.objects.create(screen=self.screen,
                                             name='Tables')
        self.seat(number=4, layout=other)
        self.assertEqual(self.seats(), [self.stalls, self.circle])

    def test_the_second_call_makes_no_query(self):
        self.seats()
        with self.assertNumQueries(0):
            self.seats()

    def test_changing_a_seat_clears_it(self):
        self.seats()
        self.stalls.is_active = False
        self.stalls.save()
        self.assertEqual(self.seats(), [self.circle])

    def test_a_new_fixed_seat_reaches_every_layout(self):
        self.seats()
        added = self.seat(number=5, area=Seat.Area.CIRCLE, row_label='A')
        self.assertIn(added, self.seats())

    def test_deleting_a_seat_clears_it(self):
        self.seats()
        self.circle.delete()
        self.assertEqual(self.seats(), [self.stalls])
