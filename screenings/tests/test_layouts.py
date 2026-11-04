from django.db import IntegrityError
from django.test import TestCase

from screenings.models import Screen, SeatingLayout


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
