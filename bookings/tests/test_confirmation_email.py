from smtplib import SMTPException
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.test import TestCase

from bookings.models import Booking, OutboundEmail
from bookings.services import confirm_booking, start_booking
from bookings.tests.test_holds import make_screening
from screenings.models import ScreeningPrice, TicketType


class ConfirmationEmailTests(TestCase):
    """Confirming a booking queues one confirmation email, sent after
    the commit (journey 6; architecture 4.32, "One confirmation
    function")."""

    def setUp(self):
        screening, (seat_1, seat_2) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        student = TicketType.objects.get(name='Student')
        for ticket_type in (adult, student):
            ScreeningPrice.objects.create(screening=screening,
                                          ticket_type=ticket_type,
                                          price_pence=950)
        self.user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.booking = start_booking(
            screening, [(seat_1, adult), (seat_2, student)], 0, 'a',
            user=self.user,
        )

    def confirm(self):
        with self.captureOnCommitCallbacks(execute=True):
            confirm_booking(self.booking)

    def test_the_customer_is_sent_their_booking(self):
        self.confirm()
        sent, = mail.outbox
        self.assertEqual(sent.to, ['customer@example.com'])
        self.assertIn(self.booking.reference, sent.subject)
        for words in (self.booking.reference, 'Nosferatu',
                      'Stalls, seat 1, Adult',
                      'Stalls, seat 2, Student. Bring proof of age or status',
                      'fictional venue'):
            with self.subTest(words=words):
                self.assertIn(words, sent.body)
                self.assertIn(words, sent.alternatives[0][0])

    def test_it_goes_through_the_outbox(self):
        self.confirm()
        email = OutboundEmail.objects.get()
        self.assertEqual((email.kind, email.booking, email.status),
                         (OutboundEmail.Kind.CONFIRMATION, self.booking,
                          OutboundEmail.Status.SENT))

    def test_confirming_twice_sends_one_email(self):
        self.confirm()
        self.confirm()
        self.assertEqual(len(mail.outbox), 1)

    def test_a_booking_with_no_account_gets_no_email(self):
        """A walk-up sale at the venue needs no email (4.14)."""
        self.booking.user = None
        self.booking.save()
        self.confirm()
        self.assertFalse(OutboundEmail.objects.exists())

    def test_an_email_that_cant_be_sent_leaves_the_booking_paid(self):
        """The testing doc's failure mode: the booking stands."""
        with mock.patch.object(EmailMultiAlternatives, 'send',
                               side_effect=SMTPException('Mail is down')):
            self.confirm()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PAID)
        email = OutboundEmail.objects.get()
        self.assertEqual((email.status, email.attempts),
                         (OutboundEmail.Status.QUEUED, 1))
