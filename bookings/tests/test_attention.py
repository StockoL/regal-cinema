from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, OutboundEmail
from bookings.tests.test_holds import make_screening

User = get_user_model()


class AttentionPageTests(TestCase):
    """One page listing what needs a person, each with its action
    (journey 12, "Needs attention"; architecture 4.32)."""

    url = '/staff/bookings/attention/'

    def setUp(self):
        self.screening, _ = make_screening()
        self.customer = User.objects.create_user('jo@example.com',
                                                 'a-long-pw-1')
        self.staff = User.objects.create_user('staff@example.com',
                                              'a-long-pw-1', is_staff=True)
        self.staff.groups.add(Group.objects.get(name='FrontOfHouse'))
        self.client.force_login(self.staff)

    def pending(self, minutes, **fields):
        return Booking.objects.create(
            screening=self.screening, user=self.customer,
            stripe_checkout_session_id=f'cs_fake_{minutes}',
            checkout_started_at=timezone.now() - timedelta(minutes=minutes),
            **fields,
        )

    def test_the_address(self):
        self.assertEqual(reverse('bookings_staff:attention'), self.url)

    def test_it_needs_the_attention_permission(self):
        self.staff.groups.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_a_stuck_payment_is_listed_with_check_with_stripe(self):
        booking = self.pending(minutes=6)
        response = self.client.get(self.url)
        self.assertContains(response, booking.reference)
        self.assertContains(response, 'jo@example.com')
        self.assertContains(response, 'Nosferatu')
        check = reverse('bookings_staff:check_with_stripe',
                        args=[booking.reference])
        self.assertContains(response, f'action="{check}"')

    def test_only_sessions_5_minutes_to_24_hours_old_are_listed(self):
        """Younger ones are left to the webhook. Older ones expired
        long ago and were checked by the scheduled job."""
        for minutes in (4, 24 * 60 + 1):
            booking = self.pending(minutes)
            with self.subTest(minutes=minutes):
                self.assertNotContains(self.client.get(self.url),
                                       booking.reference)

    def test_a_paid_booking_isnt_listed(self):
        booking = self.pending(minutes=6, status=Booking.Status.PAID)
        self.assertNotContains(self.client.get(self.url), booking.reference)

    def test_with_nothing_to_do_it_says_so(self):
        self.assertContains(self.client.get(self.url),
                            'Nothing needs attention.')

    def outbox(self, minutes, **fields):
        email = OutboundEmail.objects.create(
            kind=OutboundEmail.Kind.CONFIRMATION, recipient='jo@example.com',
            subject='Your booking', text_body='Your seats', **fields,
        )
        OutboundEmail.objects.filter(pk=email.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes),
        )
        return email

    def test_a_failed_email_is_listed_with_its_error(self):
        self.outbox(10, status=OutboundEmail.Status.FAILED, attempts=5,
                    last_error='Mail server refused the address')
        response = self.client.get(self.url)
        self.assertContains(response, 'Emails not sent (1)')
        self.assertContains(response, 'Mail server refused the address')
        self.assertContains(response, 'Confirmation')

    def test_an_email_queued_over_an_hour_is_listed(self):
        """The scheduled check runs hourly, so by then a retry has
        failed or never ran."""
        self.outbox(61)
        self.assertContains(self.client.get(self.url), 'Emails not sent (1)')

    def test_a_recent_or_sent_email_isnt_listed(self):
        self.outbox(30)
        self.outbox(120, status=OutboundEmail.Status.SENT)
        self.assertNotContains(self.client.get(self.url), 'Emails not sent')
