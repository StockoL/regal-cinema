from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegisterForm


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
        return redirect('screenings:screening_list')
    return render(request, 'accounts/register.html', {'form': form})
