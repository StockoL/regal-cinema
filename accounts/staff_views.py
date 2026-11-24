from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from staff.views import staff_permission_required

from .models import SYSTEM_USER_EMAIL
from .services import (
    NotACustomerAccount,
    deactivate_account,
    reactivate_account,
)


@staff_permission_required('bookings.view_bookings')
def customer(request):
    """Look a customer up by their email and see their account with
    every booking under it (4.32). The address must match in full, so
    one account is shown, never a list of near matches."""
    email = request.GET.get('email', '').strip()
    account = None
    bookings = []
    if email:
        account = get_user_model().objects.filter(email__iexact=email).first()
    if account and not account.is_staff and account.email != SYSTEM_USER_EMAIL:
        bookings = list(
            account.bookings.select_related('screening__film')
            .order_by('-screening__date_time')
        )
    return render(request, 'accounts/staff/customer.html', {
        'email': email, 'account': account, 'bookings': bookings,
        'system_email': SYSTEM_USER_EMAIL,
    })


@require_POST
@staff_permission_required('accounts.deactivate_account')
def account_access(request, pk):
    """Deactivate or reactivate a customer account, saying why, then go
    back to the customer (4.32). The form names what it asks for, so a
    second click finds it done and changes nothing."""
    account = get_object_or_404(get_user_model(), pk=pk)
    active = request.POST.get('active') == '1'
    reason = request.POST.get('reason', '').strip()
    change = reactivate_account if active else deactivate_account
    if not reason:
        messages.error(request, 'Say why, so the log explains it later.')
    else:
        try:
            changed = change(account, request.user, reason)
        except NotACustomerAccount:
            raise Http404 from None
        if not changed:
            state = 'active' if active else 'deactivated'
            messages.info(request, f'{account.email} was already {state}.')
        elif active:
            messages.success(request, f'{account.email} can log in again.')
        else:
            messages.success(request, f'{account.email} is deactivated '
                                      f'and signed out.')
    return redirect(f"{reverse('accounts_staff:customer')}?"
                    f"{urlencode({'email': account.email})}")
