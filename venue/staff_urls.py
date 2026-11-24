from django.urls import path

from . import staff_views

app_name = 'venue_staff'

# Mounted under /staff/venue/ (4.25).
urlpatterns = [
    path('online-sales/', staff_views.online_sales, name='online_sales'),
]
