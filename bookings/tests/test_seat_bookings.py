from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from bookings.models import Booking, SeatBooking
from bookings.tests.test_holds import make_screening
from screenings.models import TicketType


class SeatBookingTests(TestCase):
    """A sold seat, kept for good even once released (architecture 4.2,
    4.8)."""

    def setUp(self):
        self.screening, (self.seat, _) = make_screening()
        self.adult = TicketType.objects.get(name='Adult')

    def sell(self, **fields):
        booking = Booking.objects.create(screening=self.screening)
        return SeatBooking.objects.create(
            booking=booking, screening=self.screening, seat=self.seat,
            ticket_type=self.adult, price_pence=950, vat_rate_percent=20,
            **fields,
        )

    def test_a_sold_seat_keeps_its_price_and_vat_rate(self):
        sold = self.sell()
        sold.refresh_from_db()
        self.assertEqual((sold.price_pence, sold.vat_rate_percent), (950, 20))
        self.assertIsNone(sold.released_at)

    def test_a_seat_can_only_be_sold_once_per_screening(self):
        self.sell()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.sell()

    def test_a_released_seat_can_be_sold_again(self):
        first = self.sell(released_at=timezone.now())
        self.sell()
        self.assertTrue(SeatBooking.objects.filter(pk=first.pk).exists())
