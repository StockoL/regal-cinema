from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from screenings.models import Screen, Seat


class SeedSeatsTests(TestCase):
    """The demo seat plan for Screen 1 (architecture 4.1). It's demo data
    for a fictional venue, loaded by hand, not by a migration."""

    def seed(self):
        call_command('seed_seats', stdout=StringIO())
        return Screen.objects.get(name='Screen 1')

    def test_the_default_layout_gives_the_usual_capacity(self):
        """46 stalls seats, 140 circle seats and the two boxes."""
        self.assertEqual(self.seed().capacity, 188)

    def test_standard_is_the_default_and_tables_is_the_other(self):
        screen = self.seed()
        layouts = {l.name: l for l in screen.layouts.all()}
        self.assertEqual(set(layouts), {'Standard', 'Tables'})
        self.assertTrue(layouts['Standard'].is_default)
        self.assertEqual(layouts['Standard'].seats.count(), 46)
        self.assertEqual(layouts['Tables'].seats.count(), 36)

    def test_the_circle_is_fixed_with_five_rows(self):
        circle = self.seed().seats.filter(area=Seat.Area.CIRCLE)
        self.assertFalse(circle.filter(layout__isnull=False).exists())
        self.assertEqual(
            set(circle.exclude(row_label='Box')
                .values_list('row_label', flat=True)),
            set('ABCDE'),
        )

    def test_every_layout_has_wheelchair_spaces_with_companions(self):
        for layout in self.seed().layouts.all():
            with self.subTest(layout=layout.name):
                self.assertEqual(
                    layout.seats.filter(is_wheelchair_space=True).count(), 2
                )
                self.assertEqual(
                    layout.seats.filter(is_companion_seat=True).count(), 2
                )

    def test_no_wheelchair_space_is_in_the_circle(self):
        self.assertFalse(self.seed().seats.filter(
            area=Seat.Area.CIRCLE, is_wheelchair_space=True,
        ).exists())

    def test_every_table_seats_four(self):
        tables = self.seed().layouts.get(name='Tables').seats.exclude(
            table_number=None
        )
        for number in tables.values_list('table_number', flat=True).distinct():
            with self.subTest(table=number):
                self.assertEqual(tables.filter(table_number=number).count(), 4)

    def test_the_boxes_read_as_boxes(self):
        labels = {seat.label for seat in self.seed().seats.filter(
            row_label='Box'
        )}
        self.assertEqual(labels, {'Box C', 'Box D'})

    def test_every_seat_passes_validation(self):
        for seat in self.seed().seats.all():
            seat.full_clean()

    def test_running_it_again_changes_nothing(self):
        self.seed()
        out = StringIO()
        call_command('seed_seats', stdout=out)
        self.assertEqual(Seat.objects.count(), 46 + 36 + 142)
        self.assertIn('already has seats', out.getvalue())
