from django.db.models import ProtectedError
from django.test import TestCase

from accounts.models import get_system_user
from bookings.models import Booking, Refund
from bookings.services import send_refund
from bookings.tests.test_holds import make_screening
from payments.fake import FakeProvider


class RefundModelTests(TestCase):
    """One row per refund, kept even when it fails (architecture 4.2)."""

    def setUp(self):
        screening, _ = make_screening()
        self.booking = Booking.objects.create(
            screening=screening, stripe_payment_intent_id='pi_first',
        )

    def refund(self, **fields):
        return Refund.objects.create(
            booking=self.booking, amount_pence=950,
            reason='Paid after the seats were sold',
            stripe_payment_intent_id='pi_second',
            created_by=get_system_user(), **fields,
        )

    def test_a_new_refund_is_pending_until_the_provider_answers(self):
        refund = self.refund()
        self.assertEqual(refund.status, Refund.Status.PENDING)
        self.assertIsNone(refund.stripe_refund_id)
        self.assertEqual(refund.error, '')
        self.assertIsNotNone(refund.created_at)

    def test_a_booking_with_a_refund_cant_be_deleted(self):
        """4.21: financial records are protected."""
        self.refund()
        with self.assertRaises(ProtectedError):
            self.booking.delete()

    def test_a_refund_goes_back_to_its_own_payment(self):
        """A duplicate payment is refunded against itself, not the
        payment that paid for the booking (4.32)."""
        FakeProvider.reset()
        refund = self.refund()
        send_refund(refund.pk)
        refund.refresh_from_db()
        self.assertEqual(
            FakeProvider.refunds[refund.stripe_refund_id]['payment_intent_id'],
            'pi_second',
        )
