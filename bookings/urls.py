from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('screenings/<int:pk>/', views.screening_seats,
         name='screening_seats'),
]
