from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from screenings.models import (
    Film,
    Screen,
    Screening,
    ScreeningPrice,
    SeatingLayout,
    TicketClass,
    TicketType,
)
from screenings.services import fill_prices


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
