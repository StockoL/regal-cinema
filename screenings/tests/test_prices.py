from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from screenings.models import (
    Film,
    Screen,
    Screening,
    ScreeningPrice,
    TicketClass,
    TicketType,
)


class ScreeningPriceTests(TestCase):
    """One price per ticket type per screening (architecture 4.1)."""

    def setUp(self):
        self.screening = Screening.objects.create(
            film=Film.objects.create(title='Paddington', duration_minutes=95),
            screen=Screen.objects.create(name='Screen 1'),
            ticket_class=TicketClass.objects.create(name='Family Super Saver'),
            date_time=datetime(2026, 11, 15, 11, 0,
                               tzinfo=ZoneInfo('Europe/London')),
        )
        self.adult = TicketType.objects.create(name='Adult')
        self.child = TicketType.objects.create(name='Child')

    def test_each_ticket_type_has_its_own_price(self):
        """A family of two adults and two children pays two prices."""
        ScreeningPrice.objects.create(
            screening=self.screening, ticket_type=self.adult, price_pence=950
        )
        ScreeningPrice.objects.create(
            screening=self.screening, ticket_type=self.child, price_pence=650
        )
        prices = {
            price.ticket_type.name: price.price_pence
            for price in self.screening.prices.all()
        }
        self.assertEqual(prices, {'Adult': 950, 'Child': 650})

    def test_one_price_per_ticket_type_per_screening(self):
        ScreeningPrice.objects.create(
            screening=self.screening, ticket_type=self.adult, price_pence=950
        )
        with self.assertRaises(IntegrityError):
            ScreeningPrice.objects.create(
                screening=self.screening, ticket_type=self.adult,
                price_pence=800,
            )

    def test_negative_price_is_rejected(self):
        price = ScreeningPrice(
            screening=self.screening, ticket_type=self.adult, price_pence=-1
        )
        with self.assertRaises(ValidationError):
            price.full_clean()

    def test_prices_go_with_a_deleted_screening(self):
        """CASCADE, architecture 4.21: a screening created in error,
        before any bookings, takes its prices with it."""
        ScreeningPrice.objects.create(
            screening=self.screening, ticket_type=self.adult, price_pence=950
        )
        self.screening.delete()
        self.assertEqual(ScreeningPrice.objects.count(), 0)

    def test_a_priced_ticket_type_cant_be_deleted(self):
        ScreeningPrice.objects.create(
            screening=self.screening, ticket_type=self.adult, price_pence=950
        )
        with self.assertRaises(ProtectedError):
            self.adult.delete()

    def test_string_shows_ticket_type_and_price(self):
        price = ScreeningPrice.objects.create(
            screening=self.screening, ticket_type=self.adult, price_pence=950
        )
        self.assertEqual(str(price), 'Adult: £9.50')
