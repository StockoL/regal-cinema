from django.contrib.auth import get_user_model
from django.shortcuts import render

from staff.views import staff_permission_required

from .models import SYSTEM_USER_EMAIL


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
