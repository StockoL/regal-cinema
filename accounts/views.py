from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render

from .forms import RegisterForm
from .verification import send_verification_email, verify


def register(request):
    """Create an account and log straight in. Verification never blocks
    a booking (4.16)."""
    if request.user.is_authenticated:
        return redirect('screenings:screening_list')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(
            request, user,
            backend='django.contrib.auth.backends.ModelBackend',
        )
        send_verification_email(request, user)
        return redirect('screenings:screening_list')
    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request, token):
    """The link in the verification email. It works whether or not the
    customer is logged in, since it may be opened on another device."""
    user = verify(token)
    return render(request, 'accounts/verify_email_result.html', {
        'verified': user is not None,
    })


@require_POST
@login_required
def resend_verification(request):
    """Send the verification link again, from the reminder banner."""
    send_verification_email(request, request.user)
    messages.success(
        request, f"We've sent a new link to {request.user.email}."
    )
    next_page = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(
            next_page, allowed_hosts={request.get_host()}):
        next_page = 'screenings:screening_list'
    return redirect(next_page)
