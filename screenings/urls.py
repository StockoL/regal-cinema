from django.urls import path

from . import views

app_name = 'screenings'

urlpatterns = [
    path('', views.screening_list, name='screening_list'),
]
