from django.contrib.auth import login
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
