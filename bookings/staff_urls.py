from django.urls import path

from . import staff_views

app_name = 'bookings_staff'

# Mounted under /staff/bookings/ (4.25).
urlpatterns = [
    path('cancellations/', staff_views.cancellation_list,
         name='cancellation_list'),
    path('cancellations/<int:pk>/approve/', staff_views.cancellation_approve,
         name='cancellation_approve'),
    path('cancellations/<int:pk>/decline/', staff_views.cancellation_decline,
         name='cancellation_decline'),
    path('check-in/', staff_views.check_in_search, name='check_in'),
    path('check-in/<str:reference>/', staff_views.check_in_booking,
         name='check_in_booking'),
    path('check-with-stripe/<str:reference>/',
         staff_views.check_with_stripe, name='check_with_stripe'),
    path('screenings/<int:pk>/guests/', staff_views.guest_list,
         name='guest_list'),
    path('screenings/<int:pk>/guests/download/',
         staff_views.guest_list_download, name='guest_list_download'),
    path('screenings/', staff_views.screening_list, name='screening_list'),
]
