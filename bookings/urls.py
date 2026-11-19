from django.urls import path

from . import views, webhooks

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
    path('booking/<str:reference>/pay/', views.booking_pay,
         name='booking_pay'),
    path('booking/<str:reference>/confirming/', views.booking_confirming,
         name='booking_confirming'),
    path('payments/webhook/', webhooks.stripe_webhook,
         name='stripe_webhook'),
]
