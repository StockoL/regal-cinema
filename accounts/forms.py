from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

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
