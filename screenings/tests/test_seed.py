from datetime import datetime
from io import StringIO
from zoneinfo import ZoneInfo

from django.core.management import CommandError, call_command
from django.test import TestCase

from screenings.models import Film, Screen, Screening, Seat, TicketClass


class SeedSeatsTests(TestCase):
    """The demo seat plan for Screen 1 (architecture 4.1). It's demo data
    for a fictional venue, loaded by hand, not by a migration."""

    def seed(self):
        call_command('seed_seats', stdout=StringIO())
        return Screen.objects.get(name='Screen 1')

    def test_the_default_layout_gives_the_usual_capacity(self):
        """46 stalls seats and 140 circle seats."""
        self.assertEqual(self.seed().capacity, 186)

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
        self.assertEqual(circle.count(), 140)
        self.assertEqual(
            set(circle.values_list('row_label', flat=True)), set('ABCDE')
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

    def test_every_seat_passes_validation(self):
        for seat in self.seed().seats.all():
            seat.full_clean()

    def test_running_it_again_changes_nothing(self):
        self.seed()
        out = StringIO()
        call_command('seed_seats', stdout=out)
        self.assertEqual(Seat.objects.count(), 46 + 36 + 140)
        self.assertIn('already has seats', out.getvalue())


class SeedSeatsReplaceTests(TestCase):
    """--replace clears Screen 1's plan and seeds it again, so a change
    to the plan can be applied to a database that already has one."""

    def seed(self, *args):
        out = StringIO()
        call_command('seed_seats', *args, stdout=out)
        return out.getvalue()

    def test_replace_rebuilds_the_plan(self):
        self.seed()
        screen = Screen.objects.get(name='Screen 1')
        screen.seats.filter(area=Seat.Area.CIRCLE).first().delete()
        self.seed('--replace')
        self.assertEqual(screen.seats.filter(area=Seat.Area.CIRCLE).count(),
                         140)
        self.assertEqual(screen.layouts.count(), 2)

    def test_replace_is_refused_once_a_screening_uses_the_plan(self):
        self.seed()
        screen = Screen.objects.get(name='Screen 1')
        Screening.objects.create(
            film=Film.objects.create(title='A film', duration_minutes=90),
            screen=screen, layout=screen.layouts.get(is_default=True),
            ticket_class=TicketClass.objects.create(name='Standard'),
            date_time=datetime(2026, 11, 14, 19, 0,
                               tzinfo=ZoneInfo('Europe/London')),
        )
        with self.assertRaises(CommandError):
            self.seed('--replace')
        self.assertEqual(screen.seats.count(), 46 + 36 + 140)
