import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, SeatHold
from screenings.models import (
    Film,
    Screen,
    Screening,
    ScreeningClosedArea,
    ScreeningPrice,
    Seat,
    SeatingLayout,
    TicketClass,
    TicketType,
)


def text_of(html):
    """What's read out: the page with its tags taken away."""
    return re.sub(r'<[^>]+>', '', html)


def make_future_screening(**fields):
    screen = Screen.objects.create(name='Screen 1')
    layout = SeatingLayout.objects.create(screen=screen, name='Rows')
    start = timezone.now() + timedelta(days=2)
    return Screening.objects.create(
        film=Film.objects.create(title='Nosferatu', duration_minutes=100,
                                 age_rating='PG'),
        screen=screen, layout=layout,
        ticket_class=TicketClass.objects.create(name='Standard'),
        date_time=fields.pop('date_time', start), **fields,
    )


class ScreeningSeatsPageTests(TestCase):
    """The page for choosing seats at one screening (architecture 4.25;
    journey 2)."""

    def get(self, screening):
        return self.client.get(
            reverse('bookings:screening_seats', args=[screening.pk])
        )

    def test_the_address_uses_the_screening_id(self):
        self.assertEqual(
            reverse('bookings:screening_seats', args=[7]), '/screenings/7/'
        )

    def test_a_public_screening_opens(self):
        response = self.get(make_future_screening())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nosferatu')

    def test_a_private_screening_is_not_found(self):
        """Journey 1, "Private screenings hidden"."""
        response = self.get(make_future_screening(is_private=True))
        self.assertEqual(response.status_code, 404)

    def test_an_unknown_screening_is_not_found(self):
        self.assertEqual(self.client.get('/screenings/999/').status_code, 404)

    def test_an_old_link_to_a_cancelled_screening_says_so(self):
        """Architecture 4.11."""
        response = self.get(
            make_future_screening(cancelled_at=timezone.now())
        )
        self.assertContains(response, 'This screening has been cancelled',
                            status_code=410)
        self.assertContains(response, reverse('screenings:screening_list'),
                            status_code=410)

    def test_online_sales_close_at_the_listed_start(self):
        """Journey 2, "Sales closed"; architecture 4.23."""
        started = make_future_screening(
            date_time=timezone.now() - timedelta(minutes=1)
        )
        response = self.get(started)
        self.assertContains(response, 'Online sales have closed')
        self.assertContains(response, '01632 960 123')
        self.assertNotContains(response, '<form')


class SeatFormTests(TestCase):
    """The seats as a plain form that works without JavaScript, grouped
    the way a customer would look for them (wireframe 04; journey 2)."""

    def setUp(self):
        self.screening = make_future_screening()
        screen, layout = self.screening.screen, self.screening.layout
        self.stalls = [
            Seat.objects.create(
                screen=screen, layout=layout, area=Seat.Area.STALLS,
                number=n, row_index=0, column_index=n,
            )
            for n in (1, 2)
        ]
        self.circle = Seat.objects.create(
            screen=screen, area=Seat.Area.CIRCLE, row_label='A', number=24,
            row_index=0, column_index=0,
        )
        self.url = reverse('bookings:screening_seats',
                           args=[self.screening.pk])

    def page(self):
        return self.client.get(self.url).content.decode()

    def seat_input(self, seat):
        html = self.page()
        start = html.index(f'value="{seat.pk}"')
        return html[html.rindex('<input', 0, start):html.index('>', start)]

    def test_the_seats_are_drawn_area_by_area(self):
        html = self.page()
        self.assertIn('<legend class="legend">Stalls</legend>', html)
        self.assertIn('<legend class="legend">Circle</legend>', html)
        self.assertLess(html.index('>Stalls<'), html.index('>Circle<'))

    def test_each_seat_sits_at_its_place_on_the_grid(self):
        """Row and column come from the seat plan (4.1), so aisles and
        gaps are just empty cells."""
        html = self.page()
        start = html.index(f'value="{self.stalls[1].pk}"')
        label = html[html.rindex('<label', 0, start):start]
        self.assertIn('--row: 1; --col: 3', label)

    def test_each_seat_has_its_full_name_for_screen_readers(self):
        """4.17: "Circle, row A, seat 24, available", not a grid
        reference."""
        self.assertIn('Circle, row A, seat 24, available',
                      text_of(self.page()))

    def test_each_state_is_marked_for_the_styles(self):
        html = self.page()
        self.assertIn('data-seat-status="available"', html)

    def test_the_key_explains_each_state_in_words(self):
        """Nothing is shown by colour alone (4.17)."""
        html = self.page()
        for words in ('Available', 'Your seats', 'Sold',
                      'Outside section', 'Wheelchair space'):
            with self.subTest(state=words):
                self.assertIn(words, html)

    def test_each_seat_is_a_checkbox(self):
        self.assertIn('type="checkbox"', self.seat_input(self.circle))
        self.assertNotIn('disabled', self.seat_input(self.circle))

    def test_a_seat_held_by_someone_else_shows_as_sold(self):
        """4.17: to anyone else a held seat is simply unavailable."""
        SeatHold.objects.create(
            screening=self.screening, seat=self.stalls[0],
            ticket_type=TicketType.objects.get(name='Adult'),
            session_key='someone-else',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.assertIn('disabled', self.seat_input(self.stalls[0]))
        self.assertIn('Stalls, seat 1, sold', text_of(self.page()))

    def test_an_expired_hold_leaves_the_seat_free(self):
        SeatHold.objects.create(
            screening=self.screening, seat=self.stalls[0],
            ticket_type=TicketType.objects.get(name='Adult'),
            session_key='someone-else',
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertNotIn('disabled', self.seat_input(self.stalls[0]))

    def test_a_closed_area_shows_as_outside_section(self):
        """Journey 2, "Outside section"."""
        ScreeningClosedArea.objects.create(
            screening=self.screening, area=Seat.Area.CIRCLE
        )
        self.assertIn('disabled', self.seat_input(self.circle))
        self.assertIn('Circle, row A, seat 24, outside section',
                      text_of(self.page()))

    def test_a_seat_out_of_use_isnt_offered(self):
        self.stalls[1].is_active = False
        self.stalls[1].save()
        self.assertNotIn(f'value="{self.stalls[1].pk}"', self.page())

    def test_another_layouts_seats_arent_offered(self):
        tables = SeatingLayout.objects.create(
            screen=self.screening.screen, name='Tables'
        )
        other = Seat.objects.create(
            screen=self.screening.screen, layout=tables,
            area=Seat.Area.STALLS, number=9, row_index=0, column_index=9,
        )
        self.assertNotIn(f'value="{other.pk}"', self.page())

    def test_a_wheelchair_space_says_so(self):
        self.stalls[0].is_wheelchair_space = True
        self.stalls[0].save()
        self.assertIn('Stalls, seat 1, available, wheelchair space',
                      text_of(self.page()))

    def test_the_page_says_the_circle_is_stairs_only(self):
        """Journey 2, "Accessibility note"."""
        self.assertIn('The circle is reached by stairs only.', self.page())


class ChooseSeatsTests(TestCase):
    """Continuing with the chosen seats. They're kept in the session and
    not held yet: holding needs a ticket type for each (4.8 step 3)."""

    def setUp(self):
        self.screening = make_future_screening()
        self.seats = [
            Seat.objects.create(
                screen=self.screening.screen, layout=self.screening.layout,
                area=Seat.Area.STALLS, number=n, row_index=0, column_index=n,
            )
            for n in (1, 2, 3)
        ]
        self.url = reverse('bookings:screening_seats',
                           args=[self.screening.pk])
        self.tickets_url = reverse('bookings:screening_tickets',
                                   args=[self.screening.pk])

    def choose(self, *seats):
        return self.client.post(self.url,
                                {'seats': [seat.pk for seat in seats]})

    def test_continuing_goes_to_the_ticket_types(self):
        response = self.choose(self.seats[0], self.seats[2])
        self.assertRedirects(response, self.tickets_url)
        page = self.client.get(self.tickets_url)
        self.assertContains(page, 'Stalls, seat 1')
        self.assertContains(page, 'Stalls, seat 3')
        self.assertNotContains(page, 'Stalls, seat 2')

    def test_choosing_doesnt_hold_anything_yet(self):
        self.choose(self.seats[0])
        self.assertFalse(SeatHold.objects.exists())

    def test_choosing_nothing_says_so(self):
        response = self.choose()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose at least one seat.')

    def test_a_seat_from_another_screen_is_ignored(self):
        other = Seat.objects.create(
            screen=Screen.objects.create(name='Screen 2'),
            area=Seat.Area.STALLS, number=9, row_index=0, column_index=0,
        )
        self.choose(self.seats[0], other)
        page = self.client.get(self.tickets_url)
        self.assertEqual([s for s, _ in page.context['seats']],
                         [self.seats[0]])

    def test_going_back_keeps_the_seats_ticked(self):
        """Journey 2, "Amend": going back loses nothing."""
        self.choose(self.seats[1])
        html = self.client.get(self.url).content.decode()
        start = html.index(f'value="{self.seats[1].pk}"')
        self.assertIn('checked', html[start:html.index('>', start)])

    def test_the_tickets_step_needs_seats_first(self):
        self.assertRedirects(self.client.get(self.tickets_url), self.url)


@override_settings(SEAT_HOLD_MINUTES=10)
class TicketTypesTests(TestCase):
    """A ticket type for each seat, any infants, then the seats are held
    and a pending booking made (journey 2; 4.8 step 3)."""

    def setUp(self):
        self.screening = make_future_screening()
        self.seats = [
            Seat.objects.create(
                screen=self.screening.screen, layout=self.screening.layout,
                area=Seat.Area.STALLS, number=n, row_index=0, column_index=n,
            )
            for n in (1, 2)
        ]
        self.types = {t.name: t for t in TicketType.objects.all()}
        for name, pence in (('Adult', 900), ('Child', 650),
                            ('Companion', 0)):
            ScreeningPrice.objects.create(
                screening=self.screening, ticket_type=self.types[name],
                price_pence=pence,
            )
        self.seats_url = reverse('bookings:screening_seats',
                                 args=[self.screening.pk])
        self.url = reverse('bookings:screening_tickets',
                           args=[self.screening.pk])
        self.client.post(self.seats_url,
                         {'seats': [seat.pk for seat in self.seats]})

    def submit(self, first='Adult', second='Child', infants=0):
        data = {'infants': infants}
        for seat, name in zip(self.seats, (first, second)):
            if name:
                data[f'type_{seat.pk}'] = self.types[name].pk
        return self.client.post(self.url, data)

    def test_only_priced_types_the_film_allows_are_offered(self):
        film = self.screening.film
        film.age_rating = '15'
        film.save()
        offered = self.client.get(self.url).context['ticket_types']
        self.assertEqual([t.name for t, _ in offered],
                         ['Adult', 'Companion'])

    def test_each_type_shows_its_price(self):
        self.assertContains(self.client.get(self.url), 'Child, £6.50')

    def test_the_infant_counter_is_only_offered_where_infants_can_come(self):
        self.assertContains(self.client.get(self.url), 'name="infants"')
        film = self.screening.film
        film.age_rating = '15'
        film.save()
        self.assertNotContains(self.client.get(self.url), 'name="infants"')

    def test_continuing_holds_the_seats_in_a_pending_booking(self):
        response = self.submit(infants=1)
        booking = Booking.objects.get()
        self.assertRedirects(
            response, reverse('bookings:booking_checkout',
                              args=[booking.reference])
        )
        self.assertEqual(booking.infant_count, 1)
        self.assertEqual(
            {(h.seat, h.ticket_type.name) for h in booking.holds.all()},
            {(self.seats[0], 'Adult'), (self.seats[1], 'Child')},
        )

    def test_a_logged_in_customer_owns_the_booking(self):
        user = get_user_model().objects.create_user(
            'customer@example.com', 'a-long-pw-1'
        )
        self.client.force_login(user)
        self.client.post(self.seats_url,
                         {'seats': [seat.pk for seat in self.seats]})
        self.submit()
        self.assertEqual(Booking.objects.get().user, user)

    def test_every_seat_needs_a_ticket_type(self):
        response = self.submit(second=None)
        self.assertContains(response, 'Choose a ticket type for each seat.')
        self.assertFalse(Booking.objects.exists())

    def test_a_broken_rule_is_explained_and_choices_kept(self):
        response = self.submit(first='Child', second='Child')
        self.assertContains(response, 'must come with')
        self.assertContains(response, 'selected')
        self.assertFalse(SeatHold.objects.exists())

    def test_a_seat_taken_meanwhile_is_named_and_the_rest_kept(self):
        """Journey 2, "Conflict"."""
        SeatHold.objects.create(
            screening=self.screening, seat=self.seats[1],
            ticket_type=self.types['Adult'], session_key='someone-else',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        response = self.submit(first='Adult', second='Adult')
        self.assertRedirects(response, self.seats_url,
                             fetch_redirect_response=False)
        page = self.client.get(self.seats_url)
        self.assertContains(page, 'Stalls, seat 2 was taken')
        self.assertEqual(page.context['ticked'], {self.seats[0].pk})
        self.assertFalse(Booking.objects.exists())

    def test_nothing_is_booked_once_online_sales_close(self):
        self.screening.date_time = timezone.now() - timedelta(minutes=1)
        self.screening.save()
        self.submit()
        self.assertFalse(Booking.objects.exists())


@override_settings(SEAT_HOLD_MINUTES=10)
class CheckoutPlaceholderTests(TestCase):
    """Where a pending booking goes next. Payment comes later; for now
    it shows what's held and until when."""

    def setUp(self):
        test = TicketTypesTests('setUp')
        test.client = self.client
        test.setUp()
        test.submit()
        self.booking = Booking.objects.get()
        self.url = reverse('bookings:booking_checkout',
                           args=[self.booking.reference])

    def test_shows_the_held_seats_and_when_the_hold_ends(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.booking.reference)
        self.assertContains(response, 'Stalls, seat 1, Adult')
        self.assertContains(response, 'keep these seats for you until')
        self.assertNotContains(response, 'm..')

    def test_another_visitor_cant_see_it(self):
        self.client.logout()
        self.client.cookies.clear()
        self.assertEqual(self.client.get(self.url).status_code, 404)


@override_settings(SEAT_HOLD_MINUTES=10)
class CancelPendingBookingTests(TestCase):
    """Letting held seats go before paying. Journey 2, "Cancel" and
    "Seats never stuck"; architecture 4.8 step 6."""

    def setUp(self):
        test = TicketTypesTests('setUp')
        test.client = self.client
        test.setUp()
        test.submit()
        self.screening = test.screening
        self.booking = Booking.objects.get()
        self.url = reverse('bookings:booking_cancel',
                           args=[self.booking.reference])

    def test_the_checkout_page_offers_to_cancel(self):
        page = self.client.get(reverse('bookings:booking_checkout',
                                       args=[self.booking.reference]))
        self.assertContains(page, f'action="{self.url}"')

    def test_cancelling_releases_the_seats_at_once(self):
        response = self.client.post(self.url)
        self.assertRedirects(
            response,
            reverse('bookings:screening_seats', args=[self.screening.pk]),
            fetch_redirect_response=False,
        )
        self.assertFalse(Booking.objects.exists())
        self.assertFalse(SeatHold.objects.exists())

    def test_cancelling_says_so(self):
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, 'Your seats have been released.')

    def test_a_plain_link_cant_cancel(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertTrue(Booking.objects.exists())

    def test_another_visitor_cant_cancel_it(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertTrue(SeatHold.objects.exists())


@override_settings(SEAT_HOLD_MINUTES=10)
class AmendFromThePagesTests(TestCase):
    """Going back from checkout to change anything. Journey 2, "Amend";
    architecture 4.8 step 11."""

    def setUp(self):
        test = TicketTypesTests('setUp')
        test.client = self.client
        test.setUp()
        test.submit(first='Adult', second='Child', infants=1)
        self.test = test
        self.screening, self.seats = test.screening, test.seats
        self.booking = Booking.objects.get()
        self.seats_url = test.seats_url

    def test_the_checkout_page_links_back_to_change(self):
        page = self.client.get(reverse('bookings:booking_checkout',
                                       args=[self.booking.reference]))
        self.assertContains(page, 'Change seats or tickets')
        self.assertContains(page, self.seats_url)

    def test_your_own_held_seats_are_ticked_not_sold(self):
        page = self.client.get(self.seats_url)
        self.assertEqual(page.context['ticked'],
                         {seat.pk for seat in self.seats})
        self.assertNotContains(page, ', sold')

    def test_to_anyone_else_they_are_sold(self):
        self.client.cookies.clear()
        self.assertIn('1, sold', text_of(
            self.client.get(self.seats_url).content.decode()
        ))

    def test_the_tickets_step_starts_from_the_current_choices(self):
        self.client.post(self.seats_url,
                         {'seats': [seat.pk for seat in self.seats]})
        page = self.client.get(self.test.url)
        self.assertEqual(page.context['infants'], 1)
        self.assertEqual(
            page.context['picked'][self.seats[1].pk],
            str(self.test.types['Child'].pk),
        )

    def test_changing_updates_the_same_booking(self):
        self.client.post(self.seats_url, {'seats': [self.seats[0].pk]})
        response = self.test.submit(first='Adult', second=None)
        self.assertRedirects(
            response, reverse('bookings:booking_checkout',
                              args=[self.booking.reference]),
        )
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(
            [h.seat for h in self.booking.holds.all()], [self.seats[0]]
        )

    def test_after_thirty_minutes_the_customer_chooses_again(self):
        Booking.objects.update(
            created_at=timezone.now() - timedelta(minutes=31)
        )
        self.client.post(self.seats_url,
                         {'seats': [seat.pk for seat in self.seats]})
        response = self.test.submit()
        self.assertRedirects(response, self.seats_url,
                             fetch_redirect_response=False)
        self.assertFalse(Booking.objects.exists())
        self.assertContains(self.client.get(self.seats_url),
                            'longest we can keep them')


class SeatMapKeyboardTests(TestCase):
    """What seat-map.js relies on: one tab stop and arrow keys between
    seats (architecture 4.17). The keys themselves are checked in a
    browser."""

    def setUp(self):
        self.screening = make_future_screening()
        self.seat = Seat.objects.create(
            screen=self.screening.screen, area=Seat.Area.CIRCLE,
            row_label='B', number=7, row_index=1, column_index=4,
        )
        self.html = self.client.get(reverse(
            'bookings:screening_seats', args=[self.screening.pk]
        )).content.decode()

    def test_the_page_loads_the_script(self):
        self.assertIn('src="/static/js/seat-map.js"', self.html)
        self.assertIn('defer', self.html[self.html.index('seat-map.js'):][:40])

    def test_each_seat_carries_its_place_for_the_arrow_keys(self):
        self.assertIn('data-area="circle" data-row="1" data-col="4"',
                      self.html)


class SeatStateWordingTests(TestCase):
    """A seat the customer has ticked is named as theirs, not as
    available (architecture 4.17)."""

    def test_a_ticked_seat_is_named_chosen(self):
        screening = make_future_screening()
        seat = Seat.objects.create(
            screen=screening.screen, area=Seat.Area.CIRCLE, row_label='B',
            number=7, row_index=1, column_index=4,
        )
        url = reverse('bookings:screening_seats', args=[screening.pk])
        self.client.post(url, {'seats': [seat.pk]})
        html = self.client.get(url).content.decode()
        self.assertIn('Circle, row B, seat 7, <span class="seat__state">'
                      'chosen</span>', html)


class SeatMapRowLetterTests(TestCase):
    """The circle's row letters are drawn at the start of each row, as
    on the wireframes. The stalls are numbered straight through."""

    def setUp(self):
        screening = make_future_screening()
        self.circle = Seat.objects.create(
            screen=screening.screen, area=Seat.Area.CIRCLE, row_label='B',
            number=7, row_index=1, column_index=0,
        )
        self.html = self.client.get(reverse(
            'bookings:screening_seats', args=[screening.pk]
        )).content.decode()

    def test_each_circle_row_has_its_letter_in_the_first_column(self):
        self.assertIn(
            '<span class="seat-map__row" style="--row: 2" '
            'aria-hidden="true">B</span>', self.html,
        )

    def test_circle_seats_move_over_to_make_room(self):
        start = self.html.index(f'value="{self.circle.pk}"')
        label = self.html[self.html.rindex('<label', 0, start):start]
        self.assertIn('--row: 2; --col: 2', label)
