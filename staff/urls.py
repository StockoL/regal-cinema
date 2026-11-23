from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from regal.ratelimit import rate_limit

from . import views
from .forms import StaffLoginForm

app_name = 'staff'

urlpatterns = [
    path('', views.home, name='home'),
    # Its own login page, apart from the customer site (4.9).
    # Shares one count with the customer login (4.29).
    path('login/', rate_limit('login', limit=10, window=15 * 60)(
        auth_views.LoginView.as_view(
            template_name='staff/login.html',
            authentication_form=StaffLoginForm,
            next_page=reverse_lazy('staff:home'),
        )
    ), name='login'),
]
