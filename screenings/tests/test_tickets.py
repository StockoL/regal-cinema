from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from screenings.models import TicketClass, TicketType


class TicketClassTests(TestCase):
    """How a showing is priced (architecture 4.1, 4.18)."""

    def test_default_price_is_optional(self):
        ticket_class = TicketClass.objects.create(name='Live Event')
        self.assertIsNone(ticket_class.default_price_pence)

    def test_default_price_is_stored_in_pence(self):
        ticket_class = TicketClass.objects.create(
            name='Silver Screen', default_price_pence=800
        )
        ticket_class.refresh_from_db()
        self.assertEqual(ticket_class.default_price_pence, 800)

    def test_negative_default_price_is_rejected(self):
        ticket_class = TicketClass(name='Standard', default_price_pence=-1)
        with self.assertRaises(ValidationError):
            ticket_class.full_clean()

    def test_names_are_unique(self):
        TicketClass.objects.create(name='Standard')
        with self.assertRaises(IntegrityError):
            TicketClass.objects.create(name='Standard')

    def test_new_classes_are_active(self):
        self.assertTrue(TicketClass.objects.create(name='Standard').is_active)

    def test_string_is_the_name(self):
        self.assertEqual(
            str(TicketClass.objects.create(name='Silver Screen')),
            'Silver Screen',
        )


class TicketTypeTests(TestCase):
    """Who a seated ticket is for. Infants aren't a ticket type."""

    def test_names_are_unique(self):
        TicketType.objects.create(name='Adult')
        with self.assertRaises(IntegrityError):
            TicketType.objects.create(name='Adult')

    def test_new_types_are_active(self):
        self.assertTrue(TicketType.objects.create(name='Student').is_active)

    def test_string_is_the_name(self):
        self.assertEqual(str(TicketType.objects.create(name='OAP')), 'OAP')


class TicketTypeRuleFieldTests(TestCase):
    """The flags and age limit that drive the booking rules. Nothing about
    age is written into the code (architecture 4.1)."""

    def test_a_plain_type_needs_nothing(self):
        adult = TicketType.objects.create(name='Adult')
        self.assertFalse(adult.requires_adult)
        self.assertFalse(adult.requires_proof)
        self.assertFalse(adult.is_companion)
        self.assertIsNone(adult.max_age)
        self.assertEqual(adult.description, '')

    def test_a_child_type_carries_its_rules(self):
        child = TicketType.objects.create(
            name='Child', description='Aged 2 to 11, with an adult.',
            requires_adult=True, max_age=11,
        )
        child.refresh_from_db()
        self.assertTrue(child.requires_adult)
        self.assertEqual(child.max_age, 11)
        self.assertEqual(child.description, 'Aged 2 to 11, with an adult.')

    def test_a_companion_type_is_marked(self):
        companion = TicketType.objects.create(
            name='Companion', is_companion=True, requires_proof=True,
        )
        self.assertTrue(companion.is_companion)
        self.assertTrue(companion.requires_proof)
