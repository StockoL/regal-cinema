from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse


def staff_required(view):
    """The staff area is for staff accounts. A visitor goes to the staff
    login; a customer is refused. What each member of staff may do
    inside is then decided by their permissions (4.9)."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(),
                                     reverse('staff:login'))
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def staff_permission_required(permission):
    """A staff page for one action: staff only, and then only those
    holding that action's permission. Never a role (4.9)."""
    def decorator(view):
        @staff_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.has_perm(permission):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


@staff_required
def home(request):
    """The staff area's front page, offering the tools this member of
    staff's permissions allow."""
    return render(request, 'staff/home.html')
