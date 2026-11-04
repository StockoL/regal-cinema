from django.urls import path

from . import views

app_name = 'screenings'

urlpatterns = [
    path('', views.screening_list, name='screening_list'),
    path('films/<slug:slug>/', views.film_detail, name='film_detail'),
]
