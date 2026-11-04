from django.db import IntegrityError
from django.test import TestCase

from screenings.models import Screen, Seat


class ScreenTests(TestCase):
    """Screens and their fixed seat plans (architecture 4.1)."""

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')

    def test_capacity_counts_the_seats(self):
        for number in range(1, 4):
            Seat.objects.create(
                screen=self.screen, row_label='A', number=number,
                area=Seat.Area.STALLS, row_index=0, column_index=0,
            )
        Seat.objects.create(
            screen=self.screen, row_label='K', number=1,
            area=Seat.Area.CIRCLE, row_index=0, column_index=0,
        )
        self.assertEqual(self.screen.capacity, 4)

    def test_capacity_is_zero_with_no_seats(self):
        self.assertEqual(self.screen.capacity, 0)

    def test_new_screens_are_active(self):
        self.assertTrue(self.screen.is_active)

    def test_string_is_the_name(self):
        self.assertEqual(str(self.screen), 'Screen 1')


class SeatTests(TestCase):

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')

    def test_same_seat_twice_on_one_screen_is_rejected(self):
        Seat.objects.create(
            screen=self.screen, row_label='A', number=1,
            area=Seat.Area.STALLS, row_index=0, column_index=0,
        )
        with self.assertRaises(IntegrityError):
            Seat.objects.create(
                screen=self.screen, row_label='A', number=1,
                area=Seat.Area.STALLS, row_index=0, column_index=0,
            )

    def test_same_seat_label_on_another_screen_is_allowed(self):
        other = Screen.objects.create(name='Screen 2')
        Seat.objects.create(
            screen=self.screen, row_label='A', number=1,
            area=Seat.Area.STALLS, row_index=0, column_index=0,
        )
        Seat.objects.create(
            screen=other, row_label='A', number=1,
            area=Seat.Area.STALLS, row_index=0, column_index=0,
        )
        self.assertEqual(Seat.objects.count(), 2)

    def test_deleting_a_screen_with_no_history_removes_its_seats(self):
        """Seat on Screen is CASCADE (architecture 4.21). Once a seat has
        been sold, PROTECT on the booking side blocks this delete."""
        Seat.objects.create(
            screen=self.screen, row_label='A', number=1,
            area=Seat.Area.STALLS, row_index=0, column_index=0,
        )
        self.screen.delete()
        self.assertEqual(Seat.objects.count(), 0)

    def test_string_describes_the_seat(self):
        seat = Seat.objects.create(
            screen=self.screen, row_label='C', number=4,
            area=Seat.Area.CIRCLE, row_index=0, column_index=0,
        )
        self.assertEqual(str(seat), 'Row C, seat 4, circle')

    def test_seats_order_by_row_then_number(self):
        for row, number in [('B', 2), ('A', 10), ('A', 2)]:
            Seat.objects.create(
                screen=self.screen, row_label=row, number=number,
                area=Seat.Area.STALLS, row_index=0, column_index=0,
            )
        self.assertEqual(
            [(s.row_label, s.number) for s in Seat.objects.all()],
            [('A', 2), ('A', 10), ('B', 2)],
        )
