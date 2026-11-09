from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegisterTests(TestCase):
    """Creating an account with an email and password only. Journey 4;
    architecture 4.16."""

    url = reverse('accounts:register')

    def register(self, email='new@example.com', password='a-long-password',
                 confirm=None):
        return self.client.post(self.url, {
            'email': email,
            'password1': password,
            'password2': confirm or password,
        })

    def test_the_address_is_under_account(self):
        self.assertEqual(self.url, '/account/register/')

    def test_the_form_asks_for_an_email_and_a_password_twice(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context['form'].fields),
            ['email', 'password1', 'password2'],
        )

    def test_the_password_rules_are_one_plain_hint(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'At least 8 characters.')
        self.assertContains(response, 'Confirm password')
        self.assertNotContains(response, 'too similar to your other')

    def test_registering_creates_the_account_and_logs_in(self):
        response = self.register()
        self.assertRedirects(response, reverse('screenings:screening_list'))
        user = User.objects.get(email='new@example.com')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_the_email_is_stored_in_lower_case(self):
        self.register(email='New.Person@Example.COM')
        self.assertTrue(
            User.objects.filter(email='new.person@example.com').exists()
        )

    def test_a_duplicate_email_is_refused_with_a_clear_message(self):
        """Journey 4, "Duplicate email"."""
        User.objects.create_user('taken@example.com', 'a-long-password')
        response = self.register(email='taken@example.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'An account with this email address already exists.'
        )
        self.assertEqual(User.objects.count(), 1)

    def test_the_same_email_with_different_capitals_is_a_duplicate(self):
        """Journey 4, "Email case"."""
        User.objects.create_user('taken@example.com', 'a-long-password')
        self.register(email='Taken@Example.com')
        self.assertEqual(User.objects.count(), 1)

    def test_the_passwords_must_match(self):
        response = self.register(confirm='a-different-password')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_errors_are_written_next_to_their_field(self):
        """LooseLeaf's renderer ties each error to its field (4.17)."""
        User.objects.create_user('taken@example.com', 'a-long-password')
        response = self.register(email='taken@example.com')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'class="field__error"')
