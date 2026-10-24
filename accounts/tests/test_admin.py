from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserAdminTests(TestCase):
    """The admin stays usable for one-off fixes with the custom user."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='manager@example.com', password='a-long-password'
        )
        self.client.force_login(self.admin_user)

    def test_user_list_loads(self):
        response = self.client.get(reverse('admin:accounts_user_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'manager@example.com')

    def test_user_edit_page_loads(self):
        url = reverse('admin:accounts_user_change', args=[self.admin_user.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_add_user_by_email(self):
        response = self.client.post(reverse('admin:accounts_user_add'), {
            'email': 'New.Customer@Example.com',
            'usable_password': 'true',
            'password1': 'a-long-password-123',
            'password2': 'a-long-password-123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(email='new.customer@example.com').exists()
        )
