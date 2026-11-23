from django.urls import path

from . import staff_views

app_name = 'bookings_staff'

# Mounted under /staff/bookings/ (4.25).
urlpatterns = [
    path('cancellations/', staff_views.cancellation_list,
         name='cancellation_list'),
    path('cancellations/<int:pk>/decline/', staff_views.cancellation_decline,
         name='cancellation_decline'),
]
