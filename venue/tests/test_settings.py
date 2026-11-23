from django.core.exceptions import ValidationError
from django.test import TestCase

from venue.models import VenueSettings, get_settings


class VenueSettingsTests(TestCase):
    """The venue's own choices, in one row, read through one accessor
    (architecture 4.23)."""

    def test_a_fresh_site_has_the_shipped_defaults(self):
        settings = get_settings()
        self.assertEqual(
            (settings.cancellation_cutoff_hours,
             settings.cancellation_fee_pence, settings.seat_hold_minutes,
             settings.online_sales_close_minutes, settings.trailer_minutes,
             settings.turnaround_minutes, settings.withdrawal_days,
             settings.max_tickets_per_booking),
            (24, 0, 10, 0, 20, 15, 14, 10),
        )
        self.assertEqual(
            (settings.gift_voucher_min_pounds,
             settings.gift_voucher_max_pounds,
             settings.food_order_cutoff_minutes,
             settings.bar_collection_minutes_before),
            (10, 100, 90, 30),
        )
        self.assertTrue(settings.table_service_default)
        self.assertFalse(settings.online_sales_paused)
        self.assertEqual(settings.phone, '01632 960 123')
        self.assertEqual((settings.address, settings.opening_hours), ('', ''))

    def test_there_is_only_ever_one_row(self):
        get_settings()
        VenueSettings(seat_hold_minutes=12).save()
        self.assertEqual(VenueSettings.objects.count(), 1)
        self.assertEqual(get_settings().seat_hold_minutes, 12)

    def test_a_change_is_used_straight_away(self):
        """4.23 and the edge cases: no restart needed."""
        VenueSettings.objects.update(cancellation_cutoff_hours=48)
        self.assertEqual(get_settings().cancellation_cutoff_hours, 48)

    def test_the_largest_voucher_cant_be_below_the_smallest(self):
        settings = get_settings()
        settings.gift_voucher_min_pounds = 50
        settings.gift_voucher_max_pounds = 20
        with self.assertRaises(ValidationError):
            settings.full_clean()
