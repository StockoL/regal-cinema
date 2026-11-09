import re
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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


class LoginTests(TestCase):
    """Logging in with an email address. Journey 4; architecture 4.16."""

    url = reverse('accounts:login')

    def setUp(self):
        User.objects.create_user('customer@example.com', 'a-long-password')

    def log_in(self, email='customer@example.com',
               password='a-long-password', **extra):
        return self.client.post(
            self.url, {'username': email, 'password': password, **extra}
        )

    def test_the_address_is_under_account(self):
        self.assertEqual(self.url, '/account/login/')

    def test_the_form_asks_for_an_email_address(self):
        self.assertContains(self.client.get(self.url), 'Email address')

    def test_logging_in_goes_to_whats_on(self):
        self.assertRedirects(
            self.log_in(), reverse('screenings:screening_list')
        )
        self.assertIn('_auth_user_id', self.client.session)

    def test_the_email_can_be_typed_with_any_capitals(self):
        self.log_in(email='Customer@Example.com')
        self.assertIn('_auth_user_id', self.client.session)

    def test_a_wrong_password_is_refused_in_text(self):
        response = self.log_in(password='not-the-password')
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'match an account. Check them and try again.'
        )
        self.assertNotContains(response, 'case-sensitive')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logging_in_returns_to_the_page_that_asked(self):
        film_page = '/films/nosferatu/'
        self.assertRedirects(
            self.log_in(next=film_page), film_page,
            fetch_redirect_response=False,
        )

    def test_the_page_links_to_registering(self):
        self.assertContains(
            self.client.get(self.url), reverse('accounts:register')
        )


class AnonymousOnlyTests(TestCase):
    """Log in and register are for visitors who aren't logged in.
    Journey 4, "Anonymous-only pages"."""

    def setUp(self):
        self.client.force_login(
            User.objects.create_user('customer@example.com', 'a-long-pw-1')
        )

    def test_a_logged_in_customer_is_sent_away(self):
        for name in ('accounts:login', 'accounts:register'):
            with self.subTest(page=name):
                self.assertRedirects(
                    self.client.get(reverse(name)),
                    reverse('screenings:screening_list'),
                )


class LogoutTests(TestCase):
    """Logging out changes state, so it's a form with a button, never a
    plain link (ux design, 3.IV)."""

    url = reverse('accounts:logout')

    def setUp(self):
        self.client.force_login(
            User.objects.create_user('customer@example.com', 'a-long-pw-1')
        )

    def test_logging_out_goes_to_whats_on(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('screenings:screening_list'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_a_plain_link_cannot_log_anyone_out(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)


class AccountMenuTests(TestCase):
    """The main menu offers what fits the visitor (ux design, 3.IV)."""

    def menu(self):
        html = self.client.get('/').content.decode()
        return html[html.index('<nav id="main-nav"'):html.index('</nav>')]

    def test_a_visitor_sees_log_in_and_register(self):
        menu = self.menu()
        self.assertIn(f'href="{reverse("accounts:login")}"', menu)
        self.assertIn(f'href="{reverse("accounts:register")}"', menu)
        self.assertNotIn('Log out', menu)

    def test_a_customer_sees_log_out_as_a_button(self):
        self.client.force_login(
            User.objects.create_user('customer@example.com', 'a-long-pw-1')
        )
        menu = self.menu()
        self.assertIn(f'action="{reverse("accounts:logout")}"', menu)
        self.assertIn('<button', menu)
        self.assertNotIn(f'href="{reverse("accounts:login")}"', menu)


class PasswordResetTests(TestCase):
    """Choosing a new password from a link in an email. Uses Django's
    signed tokens, so nothing new is stored (architecture 4.16)."""

    def setUp(self):
        self.user = User.objects.create_user(
            'customer@example.com', 'the-old-password'
        )

    def request_link(self, email='customer@example.com'):
        return self.client.post(
            reverse('accounts:password_reset'), {'email': email}
        )

    def link_from_email(self):
        body = mail.outbox[-1].body
        return re.search(r'https?://\S+(/account/password-reset/\S+/)',
                         body).group(1)

    def test_the_log_in_page_links_to_resetting(self):
        self.assertContains(
            self.client.get(reverse('accounts:login')),
            reverse('accounts:password_reset'),
        )

    def test_asking_sends_one_email_with_a_link(self):
        response = self.request_link()
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['customer@example.com'])
        self.assertIn('Reset your Regal Cinema password',
                      mail.outbox[0].subject)
        self.assertTrue(self.link_from_email())

    def test_an_unknown_address_gets_the_same_page_and_no_email(self):
        """The page never says whether an account exists."""
        response = self.request_link('nobody@example.com')
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_the_link_lets_the_customer_choose_a_new_password(self):
        self.request_link()
        form_page = self.client.get(self.link_from_email(), follow=True)
        self.assertContains(form_page, 'Choose a new password')
        response = self.client.post(form_page.redirect_chain[-1][0], {
            'new_password1': 'a-brand-new-password',
            'new_password2': 'a-brand-new-password',
        })
        self.assertRedirects(
            response, reverse('accounts:password_reset_complete')
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('a-brand-new-password'))

    def test_a_tampered_link_is_refused(self):
        self.request_link()
        link = self.link_from_email().replace('/set-password/', '/')
        tampered = link[:-2] + 'x/'
        response = self.client.get(tampered, follow=True)
        self.assertContains(response, 'This link has expired or been used')

    def test_a_link_only_works_once(self):
        self.request_link()
        link = self.link_from_email()
        form_page = self.client.get(link, follow=True)
        self.client.post(form_page.redirect_chain[-1][0], {
            'new_password1': 'a-brand-new-password',
            'new_password2': 'a-brand-new-password',
        })
        self.client.logout()
        response = self.client.get(link, follow=True)
        self.assertContains(response, 'This link has expired or been used')


class VerificationEmailTests(TestCase):
    """A verification email goes out on registration, but the account
    works straight away. Journey 4, "Verification"; architecture 4.16."""

    def register(self):
        return self.client.post(reverse('accounts:register'), {
            'email': 'new@example.com',
            'password1': 'a-long-password',
            'password2': 'a-long-password',
        })

    def link_from_email(self):
        return re.search(
            r'https?://\S+(/account/verify/\S+/)', mail.outbox[-1].body
        ).group(1)

    def user(self):
        return User.objects.get(email='new@example.com')

    def test_registering_sends_one_email_with_a_link(self):
        self.register()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['new@example.com'])
        self.assertIn('Confirm your email address', mail.outbox[0].subject)
        self.assertTrue(self.link_from_email())

    def test_the_account_works_before_it_is_verified(self):
        self.register()
        self.assertIsNone(self.user().email_verified_at)
        self.assertIn('_auth_user_id', self.client.session)

    def test_following_the_link_verifies_the_address(self):
        self.register()
        response = self.client.get(self.link_from_email())
        self.assertContains(response, 'Email address confirmed')
        self.assertIsNotNone(self.user().email_verified_at)

    def test_the_link_works_without_being_logged_in(self):
        """It may be opened on another device."""
        self.register()
        self.client.logout()
        self.client.get(self.link_from_email())
        self.assertIsNotNone(self.user().email_verified_at)

    def test_a_tampered_link_is_refused(self):
        self.register()
        response = self.client.get(self.link_from_email()[:-3] + 'xx/')
        self.assertContains(response, 'This link has expired or is broken')
        self.assertIsNone(self.user().email_verified_at)

    def test_an_old_link_is_refused(self):
        self.register()
        with patch('accounts.verification.LINK_MAX_AGE', -1):
            response = self.client.get(self.link_from_email())
        self.assertContains(response, 'This link has expired or is broken')
        self.assertIsNone(self.user().email_verified_at)

    def test_a_link_for_an_old_address_doesnt_verify_a_new_one(self):
        self.register()
        user = self.user()
        user.email = 'changed@example.com'
        user.save()
        self.client.get(self.link_from_email())
        user.refresh_from_db()
        self.assertIsNone(user.email_verified_at)

    def test_registration_still_works_if_the_email_cant_be_sent(self):
        with patch('accounts.verification.send_mail',
                   side_effect=SMTPException):
            response = self.register()
        self.assertRedirects(response, reverse('screenings:screening_list'))
        self.assertTrue(User.objects.filter(email='new@example.com').exists())


class VerificationBannerTests(TestCase):
    """A gentle reminder until the address is confirmed, never a gate
    (architecture 4.16)."""

    def setUp(self):
        self.user = User.objects.create_user('new@example.com', 'a-long-pw-1')

    def test_an_unverified_customer_sees_the_reminder(self):
        self.client.force_login(self.user)
        response = self.client.get('/')
        self.assertContains(response, 'Please confirm your email address')
        self.assertContains(response, 'new@example.com')

    def test_a_verified_customer_doesnt(self):
        self.user.email_verified_at = timezone.now()
        self.user.save()
        self.client.force_login(self.user)
        self.assertNotContains(
            self.client.get('/'), 'Please confirm your email address'
        )

    def test_a_visitor_doesnt(self):
        self.assertNotContains(
            self.client.get('/'), 'Please confirm your email address'
        )

    def test_the_link_can_be_sent_again(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('accounts:resend_verification'), {'next': '/films/x/'}
        )
        self.assertRedirects(response, '/films/x/',
                             fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['new@example.com'])

    def test_sending_again_says_so(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('accounts:resend_verification'), follow=True
        )
        self.assertContains(response, 'sent a new link to new@example.com')

    def test_sending_again_needs_a_post_and_a_login(self):
        url = reverse('accounts:resend_verification')
        self.assertRedirects(
            self.client.post(url), f"{reverse('accounts:login')}?next={url}"
        )
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(len(mail.outbox), 0)
