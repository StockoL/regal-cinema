from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from bookings.services import confirm_booking
from bookings.tests import test_views
from payments.fake import FakeProvider


@override_settings(SEAT_HOLD_MINUTES=10)
class ConfirmingPageTests(TestCase):
    """Where Stripe sends the customer back to. Coming back confirms
    nothing: only the webhook does (journey 6, "Confirming"; 4.13 step
    4)."""

    def setUp(self):
        test = test_views.TicketTypesTests('setUp')
        test.client = self.client
        test.setUp()
        test.submit()
        self.booking = Booking.objects.get()
        user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.booking.user = user
        self.booking.save()
        self.client.force_login(user)
        self.url = reverse('bookings:booking_confirming',
                           args=[self.booking.reference])

    def test_a_pending_booking_is_still_being_confirmed(self):
        response = self.client.get(self.url)
        self.assertContains(response, "We're confirming your payment")
        self.assertContains(response, "We'll email you as soon as")
        self.assertContains(response, f'href="{self.url}"')
        self.assertNotContains(response, 'Booking confirmed')

    def test_a_paid_booking_shows_its_seats(self):
        confirm_booking(self.booking)
        response = self.client.get(self.url)
        self.assertContains(response, 'Booking confirmed')
        self.assertContains(response, self.booking.reference)
        self.assertContains(response, 'Stalls, seat 1, Adult')
        self.assertContains(response, 'Stalls, seat 2, Child')

    def test_another_visitor_cant_see_it(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_a_late_payment_says_it_was_refunded(self):
        """Journey 6, "Payment after seats lost": the customer is told."""
        self.booking.status = Booking.Status.REFUNDED
        self.booking.amount_charged_pence = 1550
        self.booking.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'refunding the £15.50 you paid')
        self.assertNotContains(response, "We're confirming your payment")


@override_settings(SEAT_HOLD_MINUTES=10)
class PayTests(TestCase):
    """Choosing Pay sends the customer to Stripe's page (journey 6,
    "Sent to Stripe"; architecture 4.13 step 3)."""

    def setUp(self):
        FakeProvider.reset()
        test = test_views.TicketTypesTests('setUp')
        test.client = self.client
        test.setUp()
        test.submit()
        self.screening = test.screening
        self.booking = Booking.objects.get()
        user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.booking.user = user
        self.booking.save()
        self.client.force_login(user)
        self.checkout = reverse('bookings:booking_checkout',
                                args=[self.booking.reference])
        self.url = reverse('bookings:booking_pay',
                           args=[self.booking.reference])

    def test_the_checkout_page_has_a_pay_button(self):
        response = self.client.get(self.checkout)
        self.assertContains(response, f'action="{self.url}"')
        self.assertContains(
            response,
            '<button class="button" type="submit" data-variant="primary">'
            'Pay £15.50</button>',
            html=True,
        )

    def test_paying_goes_to_stripes_page(self):
        response = self.client.post(self.url)
        self.booking.refresh_from_db()
        session_id = self.booking.stripe_checkout_session_id
        self.assertRedirects(
            response, f'https://checkout.example.com/{session_id}',
            status_code=303, fetch_redirect_response=False,
        )

    def test_stripe_is_told_where_to_send_the_customer_back(self):
        self.client.post(self.url)
        asked = next(iter(FakeProvider.sessions.values()))
        confirming = reverse('bookings:booking_confirming',
                             args=[self.booking.reference])
        self.assertEqual(asked['success_url'],
                         f'http://testserver{confirming}')
        self.assertEqual(asked['cancel_url'],
                         f'http://testserver{self.checkout}'
                         '?payment=not-completed')

    def test_seats_whose_hold_ran_out_are_chosen_again(self):
        self.booking.holds.update(expires_at=timezone.now())
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse(
            'bookings:screening_seats', args=[self.screening.pk]
        ))
        self.assertContains(response, 'Your hold on these seats ran out')
        self.assertEqual(FakeProvider.sessions, {})

    def test_a_visitor_who_isnt_logged_in_cant_pay(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response['Location'])
        self.assertEqual(FakeProvider.sessions, {})

    def test_a_plain_link_cant_pay(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


@override_settings(SEAT_HOLD_MINUTES=10)
class PaymentNotCompletedTests(TestCase):
    """Backing out of Stripe's page (journey 6, "Payment not completed";
    architecture 4.13 step 6)."""

    def setUp(self):
        test = test_views.TicketTypesTests('setUp')
        test.client = self.client
        test.setUp()
        test.submit()
        self.booking = Booking.objects.get()
        self.url = reverse('bookings:booking_checkout',
                           args=[self.booking.reference])

    def test_coming_back_unpaid_says_nothing_was_taken(self):
        response = self.client.get(self.url, {'payment': 'not-completed'})
        self.assertContains(response, 'No payment was taken')
        self.assertContains(response, 'keep these seats for you until')

    def test_the_message_only_shows_after_stripe(self):
        self.assertNotContains(self.client.get(self.url),
                               'No payment was taken')

    def test_the_page_shows_the_total(self):
        """An Adult at £9.00 and a Child at £6.50."""
        self.assertContains(self.client.get(self.url), 'Total £15.50')

    def test_a_visitor_logs_in_to_pay(self):
        """4.16: paying needs an account. The seats move with them."""
        response = self.client.get(self.url)
        login = reverse('accounts:login')
        self.assertContains(response, f'href="{login}?next={self.url}"')
        self.assertNotContains(response, 'Pay £')

    def test_the_page_warns_against_a_real_card(self):
        """Brief decision 12: it's a course project in test mode."""
        response = self.client.get(self.url)
        self.assertContains(response, 'Never enter a real card')
        self.assertContains(response, '4242 4242 4242 4242')


@override_settings(SEAT_HOLD_MINUTES=10)
class ProofReminderTests(TestCase):
    """A ticket that needs proof says what to bring, at checkout and on
    the confirmation (journey 2, "Proof reminder"; architecture 4.2)."""

    def setUp(self):
        test = test_views.TicketTypesTests('setUp')
        test.client = self.client
        test.setUp()
        test.submit(first='Adult', second='Companion')
        self.booking = Booking.objects.get()
        user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.booking.user = user
        self.booking.save()
        self.client.force_login(user)

    def page(self, name):
        return self.client.get(reverse(f'bookings:{name}',
                                       args=[self.booking.reference]))

    def test_checkout_reminds_them_beside_the_ticket(self):
        response = self.page('booking_checkout')
        self.assertContains(response,
                            'Stalls, seat 2, Companion. Bring your CEA Card')
        self.assertContains(response, 'Stalls, seat 1, Adult<')

    def test_the_confirmation_reminds_them_too(self):
        confirm_booking(self.booking)
        self.assertContains(self.page('booking_confirming'),
                            'Stalls, seat 2, Companion. Bring your CEA Card')
