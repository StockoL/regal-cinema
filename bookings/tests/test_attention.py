from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import get_system_user
from bookings.models import Booking, OutboundEmail, Refund
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

    def refund(self, status):
        return Refund.objects.create(
            booking=self.pending(minutes=60 * 48), amount_pence=950,
            reason='Paid after the seats were sold to someone else',
            stripe_payment_intent_id='pi_1', status=status,
            error='No such payment_intent', created_by=get_system_user(),
        )

    def test_a_failed_refund_is_listed_with_stripes_reason(self):
        refund = self.refund(Refund.Status.FAILED)
        response = self.client.get(self.url)
        self.assertContains(response, 'Refunds that failed (1)')
        self.assertContains(response, refund.booking.reference)
        self.assertContains(response, '£9.50')
        self.assertContains(response, 'No such payment_intent')

    def test_a_duplicate_payment_refund_reads_as_words(self):
        refund = self.refund(Refund.Status.FAILED)
        refund.reason = Refund.DUPLICATE_PAYMENT
        refund.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'A second payment for a booking')
        self.assertNotContains(response, 'duplicate_payment')

    def test_a_refund_that_went_through_isnt_listed(self):
        self.refund(Refund.Status.SUCCEEDED)
        self.assertNotContains(self.client.get(self.url),
                               'Refunds that failed')

    def disputed(self, closed=False):
        now = timezone.now()
        return Booking.objects.create(
            screening=self.screening, user=self.customer,
            status=Booking.Status.PAID, stripe_payment_intent_id='pi_7',
            amount_charged_pence=1900, disputed_at=now,
            dispute_closed_at=now if closed else None,
        )

    def test_an_open_dispute_is_listed_with_a_link_to_stripe(self):
        """The bank's case is answered in Stripe's dashboard (4.13)."""
        booking = self.disputed()
        response = self.client.get(self.url)
        self.assertContains(response, 'Open disputes (1)')
        self.assertContains(response, booking.reference)
        self.assertContains(response, '£19.00')
        self.assertContains(
            response, 'https://dashboard.stripe.com/test/payments/pi_7',
        )

    def test_a_closed_dispute_isnt_listed(self):
        self.disputed(closed=True)
        self.assertNotContains(self.client.get(self.url), 'Open disputes')

    def duplicate(self, days):
        booking = self.disputed(closed=True)
        refund = Refund.objects.create(
            booking=booking, amount_pence=1900,
            reason=Refund.DUPLICATE_PAYMENT, stripe_payment_intent_id='pi_8',
            status=Refund.Status.SUCCEEDED, created_by=get_system_user(),
        )
        Refund.objects.filter(pk=refund.pk).update(
            created_at=timezone.now() - timedelta(days=days),
        )
        return refund

    def test_a_duplicate_payment_this_week_is_listed(self):
        """Refunded automatically, but staff should know a customer
        paid twice, in case they get in touch (4.32)."""
        refund = self.duplicate(days=6)
        response = self.client.get(self.url)
        self.assertContains(response, 'Second payments refunded (1)')
        self.assertContains(response, refund.booking.reference)
        self.assertContains(
            response, 'https://dashboard.stripe.com/test/payments/pi_8',
        )

    def test_a_duplicate_payment_over_a_week_old_isnt_listed(self):
        self.duplicate(days=8)
        self.assertNotContains(self.client.get(self.url),
                               'Second payments refunded')


class AttentionCountTests(TestCase):
    """The staff home shows how many things need a person, beside the
    link to the page (journey 12, "Needs attention")."""

    url = reverse('staff:home')

    def setUp(self):
        self.screening, _ = make_screening()
        self.staff = User.objects.create_user('staff@example.com',
                                              'a-long-pw-1', is_staff=True)
        self.staff.groups.add(Group.objects.get(name='FrontOfHouse'))
        self.client.force_login(self.staff)

    def stuck(self):
        Booking.objects.create(
            screening=self.screening,
            checkout_started_at=timezone.now() - timedelta(minutes=6),
        )

    def test_the_count_is_beside_the_link(self):
        self.stuck()
        self.stuck()
        response = self.client.get(self.url)
        self.assertContains(response, reverse('bookings_staff:attention'))
        self.assertContains(
            response,
            '<span class="badge" data-status="warning">2'
            '<span class="visually-hidden"> waiting</span></span>',
            html=True,
        )

    def test_with_nothing_waiting_there_is_no_count(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse('bookings_staff:attention'))
        self.assertNotContains(response, 'class="badge"')

    def test_staff_without_the_permission_get_no_link(self):
        self.staff.groups.clear()
        self.assertNotContains(self.client.get(self.url),
                               reverse('bookings_staff:attention'))

    def test_counting_makes_one_query_a_list_however_many_there_are(self):
        self.stuck()
        with self.assertNumQueries(9):
            self.client.get(self.url)
        for _ in range(5):
            self.stuck()
        with self.assertNumQueries(9):
            self.client.get(self.url)
