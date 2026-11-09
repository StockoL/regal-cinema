from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    AuthenticationForm,
    SetPasswordForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import User


class AdminEmailUserCreationForm(AdminUserCreationForm):
    """The admin's add-user form, asking for an email instead of a
    username."""

    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ('email',)


class EmailUserChangeForm(UserChangeForm):
    """The admin's edit-user form, bound to the custom user."""

    class Meta(UserChangeForm.Meta):
        model = User


class RegisterForm(UserCreationForm):
    """A customer's sign-up: an email and a password typed twice, and
    nothing else (4.16)."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # One plain hint instead of Django's list of four rules.
        self.fields['password1'].help_text = (
            'At least 8 characters. Not a common password, and not only '
            'numbers.'
        )
        self.fields['password2'].label = 'Confirm password'
        self.fields['password2'].help_text = ''

    def clean_email(self):
        # Lowercased before the check, so the same address with other
        # capitals is caught as a duplicate (journey 4, "Email case").
        email = User.objects.normalize_email(self.cleaned_data['email'])
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists. '
                'Log in instead, or use another address.'
            )
        return email


class LoginForm(AuthenticationForm):
    """Django's login form, without its hint that the email might be
    case-sensitive: here it never is (4.16)."""

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': (
            "That email address and password don't match an account. "
            'Check them and try again.'
        ),
    }


class NewPasswordForm(SetPasswordForm):
    """Choosing a new password from a reset link, with the same plain
    hint as registering."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].help_text = (
            'At least 8 characters. Not a common password, and not only '
            'numbers.'
        )
        self.fields['new_password2'].label = 'Confirm new password'
