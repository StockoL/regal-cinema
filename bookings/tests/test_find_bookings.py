from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from bookings.models import Booking
from bookings.services import find_bookings
from bookings.tests.test_holds import make_screening


class FindBookingsTests(TestCase):
    """One staff search box for a reference or an email address
    (journey 14, "Find a booking"; architecture 4.32)."""

    def setUp(self):
        self.screening, _ = make_screening()
        self.customer = get_user_model().objects.create_user(
            'jo.bloggs@example.com', 'a-long-pw-1'
        )
        self.booking = Booking.objects.create(
            screening=self.screening, user=self.customer,
            status=Booking.Status.PAID,
        )
        self.code = self.booking.reference[4:]

    def found(self, query, **kwargs):
        return list(find_bookings(query, **kwargs))

    def test_a_reference_is_found_however_it_is_typed(self):
        for query in (self.booking.reference,
                      self.booking.reference.lower(),
                      f'  {self.booking.reference}  ',
                      f'RGL {self.code}', f'rgl{self.code}', self.code,
                      f'{self.code[:2]} {self.code[2:]}'):
            with self.subTest(query=query):
                self.assertEqual(self.found(query), [self.booking])

    def test_part_of_an_email_address_finds_their_bookings(self):
        other = get_user_model().objects.create_user(
            'someone@example.com', 'a-long-pw-1'
        )
        Booking.objects.create(screening=self.screening, user=other,
                               status=Booking.Status.PAID)
        self.assertEqual(self.found('jo.bloggs'), [self.booking])
        self.assertEqual(self.found('JO.BLOGGS@EXAMPLE'), [self.booking])

    def test_a_booking_not_yet_paid_for_isnt_found(self):
        self.booking.status = Booking.Status.PENDING
        self.booking.save()
        self.assertEqual(self.found(self.booking.reference), [])

    def test_a_date_narrows_the_search(self):
        day = self.screening.date_time.date()
        self.assertEqual(self.found('jo.bloggs', on_date=day), [self.booking])
        self.assertEqual(
            self.found('jo.bloggs', on_date=day + timedelta(days=1)), []
        )

    def test_nothing_typed_finds_nothing(self):
        self.assertEqual(self.found('  '), [])
