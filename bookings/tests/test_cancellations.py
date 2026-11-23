from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, Cancellation, OutboundEmail
from bookings.services import (
    CancellationNotAllowed,
    cancellation_state,
    decline_cancellation,
    request_cancellation,
)
from bookings.tests.test_holds import make_screening
from staff.models import AuditLogEntry
from venue.models import VenueSettings


class CancellationModelTests(TestCase):
    """One row for each cancellation, whoever started it (architecture
    4.2)."""

    def setUp(self):
        screening, _ = make_screening()
        self.booking = Booking.objects.create(screening=screening)

    def cancellation(self, **fields):
        return Cancellation.objects.create(
            booking=self.booking, kind=Cancellation.Kind.CUSTOMER_REQUEST,
            **fields,
        )

    def test_a_new_request_waits_for_a_decision(self):
        cancellation = self.cancellation(reason='Wrong night')
        self.assertEqual(cancellation.status, Cancellation.Status.REQUESTED)
        self.assertEqual((cancellation.outcome, cancellation.fee_pence,
                          cancellation.decision_note), ('', 0, ''))
        self.assertIsNone(cancellation.decided_by)
        self.assertIsNone(cancellation.decided_at)
        self.assertIsNotNone(cancellation.requested_at)

    def test_a_booking_with_a_cancellation_cant_be_deleted(self):
        """4.21: it's part of the booking's record."""
        self.cancellation()
        with self.assertRaises(ProtectedError):
            self.booking.delete()

    def test_the_record_stays_if_the_staff_account_goes(self):
        staff = get_user_model().objects.create_user(
            'staff@example.com', 'a-long-pw-1'
        )
        cancellation = self.cancellation(decided_by=staff)
        staff.delete()
        cancellation.refresh_from_db()
        self.assertIsNone(cancellation.decided_by)


class RequestCancellationTests(TestCase):
    """A customer asking to cancel from My bookings (journey 7;
    architecture 4.22)."""

    def setUp(self):
        self.screening, _ = make_screening()
        self.booking = Booking.objects.create(
            screening=self.screening, status=Booking.Status.PAID,
        )

    def starts_in(self, hours):
        self.screening.date_time = timezone.now() + timedelta(hours=hours)
        self.screening.save()

    def test_outside_the_cutoff_the_request_is_recorded(self):
        """Journey 7, "Request outside cutoff"."""
        self.starts_in(48)
        self.assertEqual(cancellation_state(self.booking), 'open')
        request_cancellation(self.booking, reason='Wrong night')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status,
                         Booking.Status.CANCELLATION_REQUESTED)
        cancellation = self.booking.cancellations.get()
        self.assertEqual(
            (cancellation.kind, cancellation.status, cancellation.reason),
            (Cancellation.Kind.CUSTOMER_REQUEST,
             Cancellation.Status.REQUESTED, 'Wrong night'),
        )

    def test_inside_the_cutoff_its_a_phone_call(self):
        """Journey 7, "Inside cutoff": the venue's default is 24 hours."""
        self.starts_in(23)
        self.assertEqual(cancellation_state(self.booking), 'phone')
        with self.assertRaises(CancellationNotAllowed):
            request_cancellation(self.booking)
        self.assertFalse(self.booking.cancellations.exists())

    def test_the_cutoff_is_the_venues_to_set(self):
        VenueSettings.objects.update(cancellation_cutoff_hours=48)
        self.starts_in(30)
        self.assertEqual(cancellation_state(self.booking), 'phone')

    def test_a_past_booking_offers_nothing(self):
        """Journey 7, "Past or cancelled"."""
        self.starts_in(-2)
        self.assertIsNone(cancellation_state(self.booking))
        with self.assertRaises(CancellationNotAllowed):
            request_cancellation(self.booking)

    def test_a_booking_not_paid_for_offers_nothing(self):
        self.starts_in(48)
        for status in (Booking.Status.PENDING, Booking.Status.CANCELLED,
                       Booking.Status.REFUNDED,
                       Booking.Status.CANCELLATION_REQUESTED):
            with self.subTest(status=status):
                self.booking.status = status
                self.assertIsNone(cancellation_state(self.booking))

    def test_asking_twice_records_one_request(self):
        self.starts_in(48)
        request_cancellation(self.booking)
        with self.assertRaises(CancellationNotAllowed):
            request_cancellation(self.booking)
        self.assertEqual(self.booking.cancellations.count(), 1)


class CancellationPageTests(TestCase):
    """The page a customer reaches from My bookings (journey 7;
    wireframe 18)."""

    def setUp(self):
        self.screening, _ = make_screening()
        self.starts_in(48)
        self.user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.booking = Booking.objects.create(
            screening=self.screening, user=self.user,
            status=Booking.Status.PAID, amount_charged_pence=1850,
        )
        self.client.force_login(self.user)
        self.url = reverse('bookings:cancellation_request',
                           args=[self.booking.reference])

    def starts_in(self, hours):
        self.screening.date_time = timezone.now() + timedelta(hours=hours)
        self.screening.save()

    def test_the_address_is_under_my_bookings(self):
        self.assertEqual(
            self.url, f'/account/bookings/{self.booking.reference}/cancel/'
        )

    def test_it_says_what_happens_next(self):
        VenueSettings.objects.update(cancellation_fee_pence=300)
        response = self.client.get(self.url)
        for words in ('What happens next', 'a voucher for £15.50',
                      'Cancellation fee: £3.00', 'Send request',
                      'Keep my booking', self.booking.reference):
            with self.subTest(words=words):
                self.assertContains(response, words)

    def test_sending_it_records_the_request(self):
        response = self.client.post(self.url, {'reason': 'Wrong night'},
                                    follow=True)
        self.assertRedirects(response, reverse('bookings:booking_list'))
        self.assertContains(response, 'Staff will confirm')
        cancellation = self.booking.cancellations.get()
        self.assertEqual(cancellation.reason, 'Wrong night')

    def test_inside_the_cutoff_it_gives_the_box_office(self):
        """Journey 7, "Inside cutoff"."""
        VenueSettings.objects.update(opening_hours='Daily from 11am')
        self.starts_in(5)
        response = self.client.get(self.url)
        self.assertContains(response, '01632 960 123')
        self.assertContains(response, 'Daily from 11am')
        self.assertNotContains(response, 'Send request')
        self.client.post(self.url)
        self.assertFalse(self.booking.cancellations.exists())

    def test_a_past_booking_has_no_cancellation_page(self):
        """Journey 7, "Past or cancelled"."""
        self.starts_in(-2)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_someone_elses_booking_is_not_found(self):
        self.client.force_login(get_user_model().objects.create_user(
            'other@example.com', 'a-long-pw-1'
        ))
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_a_visitor_is_asked_to_log_in(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)


class DeclineCancellationTests(TestCase):
    """Staff turning a request down (journey 7, "Request declined";
    architecture 4.22)."""

    def setUp(self):
        self.screening, _ = make_screening()
        self.screening.date_time = timezone.now() + timedelta(days=3)
        self.screening.save()
        self.customer = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.staff = get_user_model().objects.create_user(
            'staff@example.com', 'a-long-pw-1', is_staff=True,
        )
        self.booking = Booking.objects.create(
            screening=self.screening, user=self.customer,
            status=Booking.Status.PAID,
        )
        self.request = request_cancellation(self.booking, 'Wrong night')

    def decline(self, note='Nearly sold out, so the seats would go empty'):
        with self.captureOnCommitCallbacks(execute=True):
            return decline_cancellation(self.request, self.staff, note)

    def test_the_booking_goes_back_to_paid(self):
        self.decline()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PAID)
        self.request.refresh_from_db()
        self.assertEqual(
            (self.request.status, self.request.decided_by,
             self.request.decision_note),
            (Cancellation.Status.DECLINED, self.staff,
             'Nearly sold out, so the seats would go empty'),
        )
        self.assertIsNotNone(self.request.decided_at)

    def test_the_decision_is_logged_with_the_staff_member(self):
        self.decline()
        entry = AuditLogEntry.objects.get()
        self.assertEqual(
            (entry.actor, entry.action_type, entry.related_booking,
             entry.reason),
            (self.staff, AuditLogEntry.Action.CANCELLATION_DECLINED,
             self.booking, 'Nearly sold out, so the seats would go empty'),
        )

    def test_the_customer_is_told_with_the_note(self):
        self.decline()
        sent, = mail.outbox
        self.assertEqual(sent.to, ['customer@example.com'])
        self.assertIn('Nearly sold out', sent.body)
        self.assertIn(self.booking.reference, sent.body)
        self.assertEqual(self.booking.emails.get().kind,
                         OutboundEmail.Kind.CANCELLATION_DECLINED)

    def test_a_note_is_needed_to_decline(self):
        with self.assertRaises(ValueError):
            self.decline(note='  ')
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, Cancellation.Status.REQUESTED)
        self.assertFalse(AuditLogEntry.objects.exists())

    def test_a_decided_request_cant_be_declined_again(self):
        self.decline()
        with self.assertRaises(CancellationNotAllowed):
            self.decline()
        self.assertEqual(AuditLogEntry.objects.count(), 1)

    def test_the_customer_can_ask_again_afterwards(self):
        self.decline()
        self.booking.refresh_from_db()
        self.assertEqual(cancellation_state(self.booking), 'open')
