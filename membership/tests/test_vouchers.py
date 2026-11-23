import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from bookings.models import Booking
from bookings.tests.test_holds import make_screening
from membership.models import Voucher


class VoucherTests(TestCase):
    """A balance that whoever holds the code can spend, for a year
    (architecture 4.4)."""

    def voucher(self, **fields):
        fields.setdefault('initial_value_pence', 1850)
        fields.setdefault('remaining_value_pence', 1850)
        fields.setdefault('source', Voucher.Source.BOOKING_CANCELLED)
        return Voucher.objects.create(**fields)

    def test_the_code_is_long_random_and_easy_to_read_out(self):
        """4.26: the code alone spends the balance, so it can't be
        guessed. No 0, O, 1, I or L, as with booking references."""
        voucher = self.voucher()
        self.assertRegex(voucher.code,
                         r'^[A-HJKMNP-Z2-9]{4}-[A-HJKMNP-Z2-9]{4}-'
                         r'[A-HJKMNP-Z2-9]{4}$')
        self.assertIsNone(re.search(r'[01OIL]', voucher.code))
        self.assertNotEqual(self.voucher().code, voucher.code)

    def test_every_voucher_lasts_a_year(self):
        voucher = self.voucher()
        self.assertAlmostEqual(voucher.expires_at,
                               timezone.now() + timedelta(days=365),
                               delta=timedelta(minutes=1))

    def test_it_can_be_spent_while_active_unexpired_and_in_credit(self):
        self.assertTrue(self.voucher().is_usable)
        self.assertFalse(self.voucher(is_active=False).is_usable)
        self.assertFalse(self.voucher(remaining_value_pence=0).is_usable)
        self.assertFalse(self.voucher(
            expires_at=timezone.now() - timedelta(days=1)
        ).is_usable)

    def test_the_balance_can_never_exceed_what_it_started_with(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.voucher(remaining_value_pence=1851)

    def test_codes_are_unique(self):
        first = self.voucher()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.voucher(code=first.code)

    def test_it_outlives_its_buyer_and_its_booking(self):
        """4.21: SET_NULL, since whoever holds the code can spend it."""
        buyer = get_user_model().objects.create_user(
            'buyer@example.com', 'a-long-pw-1'
        )
        screening, _ = make_screening()
        booking = Booking.objects.create(screening=screening)
        voucher = self.voucher(purchased_by=buyer, source_booking=booking)
        buyer.delete()
        booking.delete()
        voucher.refresh_from_db()
        self.assertIsNone(voucher.purchased_by)
        self.assertIsNone(voucher.source_booking)
