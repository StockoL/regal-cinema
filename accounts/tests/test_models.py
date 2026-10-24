from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    """The email-login user model from architecture 4.16 and journey 4."""

    def test_email_is_the_login_field(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')
        self.assertEqual(User.REQUIRED_FIELDS, [])

    def test_there_is_no_username_field(self):
        field_names = [field.name for field in User._meta.get_fields()]
        self.assertNotIn('username', field_names)

    def test_create_user_with_email_and_password(self):
        user = User.objects.create_user(
            email='customer@example.com', password='a-long-password'
        )
        self.assertEqual(user.email, 'customer@example.com')
        self.assertTrue(user.check_password('a-long-password'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_email_is_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='a-long-password')

    def test_email_is_lowercased_when_saved(self):
        user = User.objects.create_user(email='J.Smith@Example.COM')
        self.assertEqual(user.email, 'j.smith@example.com')

    def test_lookup_by_email_ignores_case(self):
        user = User.objects.create_user(email='j.smith@example.com')
        found = User.objects.get_by_natural_key('J.Smith@Example.com')
        self.assertEqual(found, user)

    def test_duplicate_email_is_rejected(self):
        """Journey 4, "Duplicate email"."""
        User.objects.create_user(email='j.smith@example.com')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='j.smith@example.com')

    def test_duplicate_email_with_different_capitals_is_rejected(self):
        """Journey 4, "Email case"."""
        User.objects.create_user(email='j.smith@example.com')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='J.Smith@example.com')

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='manager@example.com', password='a-long-password'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_superuser_must_be_staff(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email='manager@example.com',
                password='a-long-password',
                is_staff=False,
            )

    def test_string_is_the_email(self):
        user = User.objects.create_user(email='customer@example.com')
        self.assertEqual(str(user), 'customer@example.com')
