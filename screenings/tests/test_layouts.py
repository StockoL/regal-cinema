from django.db import IntegrityError
from django.test import TestCase

from screenings.models import Screen, Seat, SeatingLayout


class SeatingLayoutTests(TestCase):
    """Arrangements of a screen's stalls (architecture 4.1)."""

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')

    def test_a_screen_can_have_several_layouts(self):
        SeatingLayout.objects.create(screen=self.screen, name='Standard')
        SeatingLayout.objects.create(screen=self.screen, name='Tables')
        self.assertEqual(self.screen.layouts.count(), 2)

    def test_layout_names_are_unique_per_screen(self):
        SeatingLayout.objects.create(screen=self.screen, name='Standard')
        with self.assertRaises(IntegrityError):
            SeatingLayout.objects.create(screen=self.screen, name='Standard')

    def test_same_name_on_another_screen_is_allowed(self):
        other = Screen.objects.create(name='Screen 2')
        SeatingLayout.objects.create(screen=self.screen, name='Standard')
        SeatingLayout.objects.create(screen=other, name='Standard')
        self.assertEqual(SeatingLayout.objects.count(), 2)

    def test_only_one_layout_per_screen_is_the_default(self):
        SeatingLayout.objects.create(
            screen=self.screen, name='Standard', is_default=True
        )
        with self.assertRaises(IntegrityError):
            SeatingLayout.objects.create(
                screen=self.screen, name='Tables', is_default=True
            )

    def test_deleting_a_screen_removes_its_layouts(self):
        SeatingLayout.objects.create(screen=self.screen, name='Standard')
        self.screen.delete()
        self.assertEqual(SeatingLayout.objects.count(), 0)

    def test_string_names_the_screen_and_layout(self):
        layout = SeatingLayout.objects.create(
            screen=self.screen, name='Tables'
        )
        self.assertEqual(str(layout), 'Screen 1: Tables')


class SeatInLayoutTests(TestCase):
    """A seat is fixed, appearing in every layout, or belongs to one
    stalls arrangement. Its place on the map is a grid position (4.1)."""

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')
        self.layout = SeatingLayout.objects.create(
            screen=self.screen, name='Standard'
        )

    def make_seat(self, **fields):
        fields.setdefault('screen', self.screen)
        fields.setdefault('row_label', 'A')
        fields.setdefault('number', 1)
        fields.setdefault('area', Seat.Area.STALLS)
        fields.setdefault('row_index', 0)
        fields.setdefault('column_index', 0)
        return Seat.objects.create(**fields)

    def test_a_seat_with_no_layout_is_fixed(self):
        seat = self.make_seat(area=Seat.Area.CIRCLE)
        self.assertIsNone(seat.layout)

    def test_a_seat_can_belong_to_a_layout(self):
        seat = self.make_seat(layout=self.layout)
        self.assertEqual(list(self.layout.seats.all()), [seat])

    def test_deleting_a_layout_removes_only_its_seats(self):
        fixed = self.make_seat(area=Seat.Area.CIRCLE, row_label='K')
        self.make_seat(layout=self.layout)
        self.layout.delete()
        self.assertEqual(list(Seat.objects.all()), [fixed])

    def test_grid_position_is_stored(self):
        seat = self.make_seat(row_index=3, column_index=7)
        seat.refresh_from_db()
        self.assertEqual((seat.row_index, seat.column_index), (3, 7))
