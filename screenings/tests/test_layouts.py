from django.core.exceptions import ValidationError
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


class SeatFlagTests(TestCase):
    """Wheelchair spaces, companion seats, tables and seats out of use
    (architecture 4.1, 4.17)."""

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')

    def make_seat(self, **fields):
        fields.setdefault('screen', self.screen)
        fields.setdefault('row_label', '')
        fields.setdefault('number', 1)
        fields.setdefault('area', Seat.Area.STALLS)
        fields.setdefault('row_index', 0)
        fields.setdefault('column_index', 0)
        return Seat.objects.create(**fields)

    def test_flags_are_off_and_the_seat_in_use_by_default(self):
        seat = self.make_seat()
        self.assertFalse(seat.is_wheelchair_space)
        self.assertFalse(seat.is_companion_seat)
        self.assertTrue(seat.is_active)
        self.assertIsNone(seat.table_number)

    def test_a_stalls_seat_can_sit_at_a_table(self):
        seat = self.make_seat(table_number=4)
        seat.refresh_from_db()
        self.assertEqual(seat.table_number, 4)

    def test_a_seat_can_be_taken_out_of_use(self):
        seat = self.make_seat(is_active=False)
        self.assertFalse(Seat.objects.get(pk=seat.pk).is_active)


class WheelchairSpaceTests(TestCase):
    """The circle is reached by stairs only, so wheelchair spaces may
    only be in the stalls (architecture 4.1)."""

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')

    def make_seat(self, **fields):
        fields.setdefault('screen', self.screen)
        fields.setdefault('number', 1)
        fields.setdefault('row_index', 0)
        fields.setdefault('column_index', 0)
        return Seat(**fields)

    def test_a_wheelchair_space_in_the_stalls_is_allowed(self):
        seat = self.make_seat(area=Seat.Area.STALLS, is_wheelchair_space=True)
        seat.full_clean()

    def test_a_wheelchair_space_in_the_circle_is_refused(self):
        seat = self.make_seat(
            area=Seat.Area.CIRCLE, row_label='A', is_wheelchair_space=True
        )
        with self.assertRaises(ValidationError) as caught:
            seat.full_clean()
        self.assertIn('is_wheelchair_space', caught.exception.message_dict)
