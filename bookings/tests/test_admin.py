from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking
from bookings.services import start_booking
from bookings.tests.test_holds import make_screening
from screenings.models import ScreeningPrice, TicketType


class BookingAdminTests(TestCase):
    """Until Stripe is added, a pending booking is marked paid by hand,
    through the same confirm_booking the webhook will call (4.32)."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(
            email='manager@example.com', password='a-long-password'
        ))
        screening, (seat, _) = make_screening()
        adult = TicketType.objects.get(name='Adult')
        ScreeningPrice.objects.create(screening=screening, ticket_type=adult,
                                      price_pence=950)
        self.booking = start_booking(screening, [(seat, adult)], 0, 'a')
        self.url = reverse('admin:bookings_booking_changelist')

    def mark_paid(self):
        return self.client.post(self.url, {
            'action': 'mark_paid', '_selected_action': [self.booking.pk],
        }, follow=True)

    def test_the_list_loads(self):
        self.assertContains(self.client.get(self.url),
                            self.booking.reference)

    def test_mark_paid_confirms_the_booking(self):
        self.mark_paid()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PAID)
        self.assertEqual(self.booking.seats.count(), 1)

    def test_a_booking_with_a_lost_seat_stays_pending(self):
        self.booking.holds.all().delete()
        response = self.mark_paid()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        self.assertContains(response, 'lost a seat')
