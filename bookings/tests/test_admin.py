from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bookings.services import start_booking
from bookings.tests.test_holds import make_screening
from screenings.models import ScreeningPrice, TicketType


class BookingAdminTests(TestCase):
    """The bookings list in the admin. Only Stripe, or staff asking
    Stripe, can mark a booking paid (4.13, 4.32)."""

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

    def test_the_list_loads(self):
        self.assertContains(self.client.get(self.url),
                            self.booking.reference)

    def test_no_action_marks_a_booking_paid_without_a_payment(self):
        self.assertNotContains(self.client.get(self.url), 'Mark as paid')
