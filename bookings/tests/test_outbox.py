from django.db import IntegrityError, transaction
from django.test import TestCase

from bookings.models import Booking, OutboundEmail
from bookings.tests.test_holds import make_screening


class OutboundEmailModelTests(TestCase):
    """Every email waits in the outbox, so a failed send never undoes a
    booking and can be tried again (architecture 4.2)."""

    def setUp(self):
        screening, _ = make_screening()
        self.booking = Booking.objects.create(screening=screening)

    def email(self, kind=OutboundEmail.Kind.CONFIRMATION, **fields):
        return OutboundEmail.objects.create(
            kind=kind, booking=self.booking,
            recipient='customer@example.com', subject='Your booking',
            text_body='Your seats', **fields,
        )

    def test_a_new_email_is_queued_and_untried(self):
        email = self.email()
        self.assertEqual(email.status, OutboundEmail.Status.QUEUED)
        self.assertEqual((email.attempts, email.last_error), (0, ''))
        self.assertIsNone(email.sent_at)

    def test_a_booking_gets_one_confirmation(self):
        self.email()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.email()

    def test_a_booking_can_have_several_refund_emails(self):
        self.email(kind=OutboundEmail.Kind.REFUND_ISSUED)
        self.email(kind=OutboundEmail.Kind.REFUND_ISSUED)
        self.assertEqual(self.booking.emails.count(), 2)

    def test_an_email_outlives_its_booking(self):
        """4.21: losing the booking link is harmless."""
        email = self.email()
        self.booking.delete()
        email.refresh_from_db()
        self.assertIsNone(email.booking)
