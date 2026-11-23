from smtplib import SMTPException
from unittest import mock

from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.test import TestCase

from bookings.emails import send_outbound_email
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

    def test_a_customer_can_be_declined_more_than_once(self):
        """They can ask again after a decline (4.22)."""
        self.email(kind=OutboundEmail.Kind.CANCELLATION_DECLINED)
        self.email(kind=OutboundEmail.Kind.CANCELLATION_DECLINED)
        self.assertEqual(self.booking.emails.count(), 2)

    def test_an_email_outlives_its_booking(self):
        """4.21: losing the booking link is harmless."""
        email = self.email()
        self.booking.delete()
        email.refresh_from_db()
        self.assertIsNone(email.booking)


class SendEmailTests(TestCase):
    """Sending one email from the outbox and recording what happened
    (architecture 4.2, 4.32)."""

    def setUp(self):
        self.email = OutboundEmail.objects.create(
            kind=OutboundEmail.Kind.CONFIRMATION,
            recipient='customer@example.com', subject='Your booking',
            text_body='Your seats', html_body='<p>Your seats</p>',
        )

    def refreshed(self):
        self.email.refresh_from_db()
        return self.email

    def test_it_sends_plain_text_with_an_html_part(self):
        send_outbound_email(self.email.pk)
        sent, = mail.outbox
        self.assertEqual((sent.to, sent.subject, sent.body),
                         (['customer@example.com'], 'Your booking',
                          'Your seats'))
        self.assertEqual(sent.alternatives[0][0], '<p>Your seats</p>')
        email = self.refreshed()
        self.assertEqual((email.status, email.attempts),
                         (OutboundEmail.Status.SENT, 1))
        self.assertIsNotNone(email.sent_at)

    def test_a_sent_email_isnt_sent_again(self):
        send_outbound_email(self.email.pk)
        send_outbound_email(self.email.pk)
        self.assertEqual(len(mail.outbox), 1)

    def test_a_failure_is_kept_for_another_try(self):
        with mock.patch.object(EmailMultiAlternatives, 'send',
                               side_effect=SMTPException('Mail is down')):
            send_outbound_email(self.email.pk)
        email = self.refreshed()
        self.assertEqual((email.status, email.attempts),
                         (OutboundEmail.Status.QUEUED, 1))
        self.assertIn('Mail is down', email.last_error)

    def test_after_five_tries_it_is_marked_failed(self):
        with mock.patch.object(EmailMultiAlternatives, 'send',
                               side_effect=SMTPException('Mail is down')):
            for _ in range(5):
                send_outbound_email(self.email.pk)
        self.assertEqual(self.refreshed().status, OutboundEmail.Status.FAILED)
