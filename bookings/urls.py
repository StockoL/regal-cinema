from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('screenings/<int:pk>/', views.screening_seats,
         name='screening_seats'),
    path('screenings/<int:pk>/tickets/', views.screening_tickets,
         name='screening_tickets'),
    path('booking/<str:reference>/', views.booking_checkout,
         name='booking_checkout'),
    path('booking/<str:reference>/cancel/', views.booking_cancel,
         name='booking_cancel'),
]
