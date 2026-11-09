from django.test import TestCase

from bookings.basket import BasketError, check_basket
from screenings.models import Film, TicketType


class BasketRuleTests(TestCase):
    """The rules a basket must meet before checkout, from the Regal's
    own terms (architecture 4.2; journey 2)."""

    def setUp(self):
        self.pg = Film(title='Paddington', duration_minutes=95,
                       age_rating='PG')
        self.fifteen = Film(title='Nosferatu', duration_minutes=100,
                            age_rating='15')
        self.types = {t.name: t for t in TicketType.objects.all()}

    def tickets(self, *names):
        return [self.types[name] for name in names]

    def assert_refused(self, film, names, infants=0, says=''):
        with self.assertRaises(BasketError) as caught:
            check_basket(film, self.tickets(*names), infants)
        self.assertIn(says, str(caught.exception))

    def test_an_ordinary_basket_passes(self):
        check_basket(self.pg, self.tickets('Adult', 'Child'), 1)

    def test_a_basket_needs_a_seat(self):
        self.assert_refused(self.pg, [], says='at least one seat')

    def test_a_basket_of_only_infants_needs_a_seat_too(self):
        self.assert_refused(self.pg, [], infants=1, says='at least one seat')

    def test_child_tickets_alone_are_refused(self):
        """Journey 2, "Infants need an adult"."""
        self.assert_refused(self.pg, ['Child', 'Child'],
                            says='must come with')

    def test_infants_need_a_ticket_that_doesnt_need_an_adult(self):
        self.assert_refused(self.pg, ['Child'], infants=1,
                            says='must come with')

    def test_a_young_person_can_bring_a_child(self):
        """Young person doesn't need an adult, so it counts (4.2)."""
        check_basket(self.pg, self.tickets('Young person', 'Child'))

    def test_there_is_no_cap_on_infants(self):
        check_basket(self.pg, self.tickets('Adult'), infants=4)

    def test_infants_are_refused_on_a_15_film(self):
        """Journey 2, "Infants on suitable films"."""
        self.assert_refused(self.fifteen, ['Adult'], infants=1,
                            says='U, PG and 12A')

    def test_a_companion_comes_with_a_full_price_ticket(self):
        check_basket(self.pg, self.tickets('OAP', 'Companion'))

    def test_a_companion_alone_is_refused(self):
        self.assert_refused(self.pg, ['Companion'], says='Companion')

    def test_a_child_cant_be_the_ticket_a_companion_comes_with(self):
        self.assert_refused(self.pg, ['Child', 'Companion'],
                            says='Companion')

    def test_companions_cant_outnumber_full_price_tickets(self):
        self.assert_refused(self.pg, ['Adult', 'Companion', 'Companion'],
                            says='Companion')
