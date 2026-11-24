from django.urls import path

from . import staff_views

app_name = 'accounts_staff'

# Mounted under /staff/accounts/ (4.25).
urlpatterns = [
    path('', staff_views.customer, name='customer'),
]
