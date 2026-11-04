from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from datetime import datetime
from zoneinfo import ZoneInfo

from django.db.models import ProtectedError

from screenings.models import (
    Film,
    Screen,
    Screening,
    Seat,
    SeatingLayout,
    TicketClass,
)


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


class ScreeningLayoutTests(TestCase):
    """A screening picks one of its screen's layouts (architecture 4.1)."""

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')
        self.layout = SeatingLayout.objects.create(
            screen=self.screen, name='Standard'
        )
        self.film = Film.objects.create(title='Nosferatu', duration_minutes=100)
        self.ticket_class = TicketClass.objects.create(name='Standard')
        self.start = datetime(2026, 11, 14, 19, 0,
                              tzinfo=ZoneInfo('Europe/London'))

    def make_screening(self, **fields):
        fields.setdefault('film', self.film)
        fields.setdefault('screen', self.screen)
        fields.setdefault('layout', self.layout)
        fields.setdefault('ticket_class', self.ticket_class)
        fields.setdefault('date_time', self.start)
        return Screening(**fields)

    def test_a_screening_uses_a_layout(self):
        screening = self.make_screening()
        screening.full_clean()
        screening.save()
        self.assertEqual(list(self.layout.screenings.all()), [screening])

    def test_a_layout_from_another_screen_is_refused(self):
        other = Screen.objects.create(name='Screen 2')
        wrong = SeatingLayout.objects.create(screen=other, name='Standard')
        screening = self.make_screening(layout=wrong)
        with self.assertRaises(ValidationError) as caught:
            screening.full_clean()
        self.assertIn('layout', caught.exception.message_dict)

    def test_a_layout_in_use_cannot_be_deleted(self):
        """Screening.layout is PROTECT (architecture 4.21)."""
        self.make_screening().save()
        with self.assertRaises(ProtectedError):
            self.layout.delete()


class ScreeningSeatsTests(TestCase):
    """The seats a screening uses are the screen's fixed seats plus its
    layout's seats, less any seat out of use (architecture 4.1)."""

    def setUp(self):
        self.screen = Screen.objects.create(name='Screen 1')
        self.rows = SeatingLayout.objects.create(
            screen=self.screen, name='Rows'
        )
        self.tables = SeatingLayout.objects.create(
            screen=self.screen, name='Tables'
        )
        self.circle_a1 = self.seat(area=Seat.Area.CIRCLE, row_label='A')
        self.rows_1 = self.seat(layout=self.rows)
        self.rows_2 = self.seat(layout=self.rows, number=2, column_index=1)
        self.tables_1 = self.seat(layout=self.tables)
        self.screening = Screening.objects.create(
            film=Film.objects.create(title='Nosferatu', duration_minutes=100),
            screen=self.screen, layout=self.rows,
            ticket_class=TicketClass.objects.create(name='Standard'),
            date_time=datetime(2026, 11, 14, 19, 0,
                               tzinfo=ZoneInfo('Europe/London')),
        )

    def seat(self, **fields):
        fields.setdefault('screen', self.screen)
        fields.setdefault('area', Seat.Area.STALLS)
        fields.setdefault('number', 1)
        fields.setdefault('row_index', 0)
        fields.setdefault('column_index', 0)
        return Seat.objects.create(**fields)

    def test_fixed_seats_and_the_layouts_seats_are_included(self):
        self.assertCountEqual(
            self.screening.seats(),
            [self.circle_a1, self.rows_1, self.rows_2],
        )

    def test_another_layouts_seats_are_left_out(self):
        self.assertNotIn(self.tables_1, self.screening.seats())

    def test_a_seat_out_of_use_is_left_out(self):
        self.rows_2.is_active = False
        self.rows_2.save()
        self.assertNotIn(self.rows_2, self.screening.seats())

    def test_capacity_is_counted_from_those_seats(self):
        self.assertEqual(self.screening.capacity, 3)
