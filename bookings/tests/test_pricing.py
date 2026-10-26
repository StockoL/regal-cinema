from decimal import Decimal

from django.test import SimpleTestCase

from bookings.pricing import apply_discount


class ApplyDiscountTests(SimpleTestCase):
    """Per-ticket discounts, nearest penny, halves up (architecture
    4.10)."""

    def test_an_exact_discount(self):
        self.assertEqual(apply_discount(1000, 10), 900)

    def test_half_a_penny_rounds_the_discount_up(self):
        """10% of £9.95 is 99.5p off, which rounds to £1.00 off."""
        self.assertEqual(apply_discount(995, 10), 895)

    def test_just_under_half_a_penny_rounds_the_discount_down(self):
        """10% of £9.94 is 99.4p off, which rounds to 99p off."""
        self.assertEqual(apply_discount(994, 10), 895)

    def test_a_fractional_percentage(self):
        self.assertEqual(apply_discount(800, Decimal('12.5')), 700)

    def test_no_discount_leaves_the_price(self):
        self.assertEqual(apply_discount(995, 0), 995)

    def test_a_full_discount_makes_it_free(self):
        self.assertEqual(apply_discount(995, 100), 0)

    def test_the_result_is_whole_pence(self):
        self.assertIsInstance(apply_discount(995, 10), int)

    def test_a_negative_percentage_is_refused(self):
        with self.assertRaises(ValueError):
            apply_discount(995, -5)

    def test_more_than_100_percent_is_refused(self):
        with self.assertRaises(ValueError):
            apply_discount(995, 101)
