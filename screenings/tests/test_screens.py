from django.db import IntegrityError
from django.test import TestCase

from screenings.models import Screen, Seat, SeatingLayout


class ScreenTests(TestCase):
    """Screens and their fixed seat plans (architecture 4.1)."""

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')

    def test_capacity_counts_fixed_seats_and_the_default_layout(self):
        """The figure the admin list shows: the screen as it's normally
        laid out. A screening's own capacity is on the screening (4.1)."""
        rows = SeatingLayout.objects.create(
            screen=self.screen, name='Rows', is_default=True
        )
        tables = SeatingLayout.objects.create(
            screen=self.screen, name='Tables'
        )
        for layout, numbers in ((rows, range(1, 4)), (tables, range(1, 3))):
            for number in numbers:
                Seat.objects.create(
                    screen=self.screen, layout=layout, number=number,
                    area=Seat.Area.STALLS, row_index=0, column_index=0,
                )
        Seat.objects.create(
            screen=self.screen, row_label='K', number=1,
            area=Seat.Area.CIRCLE, row_index=0, column_index=0,
        )
        Seat.objects.create(
            screen=self.screen, row_label='K', number=2, is_active=False,
            area=Seat.Area.CIRCLE, row_index=0, column_index=1,
        )
        self.assertEqual(self.screen.capacity, 4)

    def test_capacity_with_no_default_layout_counts_fixed_seats(self):
        Seat.objects.create(
            screen=self.screen, row_label='K', number=1,
            area=Seat.Area.CIRCLE, row_index=0, column_index=0,
        )
        self.assertEqual(self.screen.capacity, 1)

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

    def test_same_seat_in_two_layouts_is_allowed(self):
        """Stalls seat 1 exists in the rows layout and the tables layout.
        They're different seats, because the arrangements differ."""
        rows = SeatingLayout.objects.create(screen=self.screen, name='Rows')
        tables = SeatingLayout.objects.create(
            screen=self.screen, name='Tables'
        )
        for layout in (rows, tables):
            Seat.objects.create(
                screen=self.screen, layout=layout, number=1,
                area=Seat.Area.STALLS, row_index=0, column_index=0,
            )
        self.assertEqual(Seat.objects.count(), 2)

    def test_same_seat_twice_in_one_layout_is_rejected(self):
        layout = SeatingLayout.objects.create(screen=self.screen, name='Rows')
        Seat.objects.create(
            screen=self.screen, layout=layout, number=1,
            area=Seat.Area.STALLS, row_index=0, column_index=0,
        )
        with self.assertRaises(IntegrityError):
            Seat.objects.create(
                screen=self.screen, layout=layout, number=1,
                area=Seat.Area.STALLS, row_index=0, column_index=0,
            )

    def test_same_label_in_stalls_and_circle_is_allowed(self):
        for area in (Seat.Area.STALLS, Seat.Area.CIRCLE):
            Seat.objects.create(
                screen=self.screen, row_label='A', number=1, area=area,
                row_index=0, column_index=0,
            )
        self.assertEqual(Seat.objects.count(), 2)

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

    def test_label_names_the_area_row_and_seat(self):
        seat = Seat.objects.create(
            screen=self.screen, row_label='C', number=4,
            area=Seat.Area.CIRCLE, row_index=0, column_index=0,
        )
        self.assertEqual(seat.label, 'Circle, row C, seat 4')
        self.assertEqual(str(seat), 'Circle, row C, seat 4')

    def test_label_leaves_out_an_empty_row(self):
        """Stalls seats are numbered straight through, with no rows."""
        seat = Seat.objects.create(
            screen=self.screen, number=20, area=Seat.Area.STALLS,
            row_index=0, column_index=0,
        )
        self.assertEqual(seat.label, 'Stalls, seat 20')

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
