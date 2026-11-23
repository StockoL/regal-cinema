from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import StaffLoginForm

app_name = 'staff'

urlpatterns = [
    path('', views.home, name='home'),
    # Its own login page, apart from the customer site (4.9).
    path('login/', auth_views.LoginView.as_view(
        template_name='staff/login.html',
        authentication_form=StaffLoginForm,
        next_page=reverse_lazy('staff:home'),
    ), name='login'),
]
