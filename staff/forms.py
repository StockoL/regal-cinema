from django import forms

from accounts.forms import LoginForm


class StaffLoginForm(LoginForm):
    """The staff login refuses a customer account outright, rather than
    logging it in only to turn it away (4.9)."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError(
                'This page is only for staff accounts. Customers log in '
                'from the main site.',
                code='not_staff',
            )
