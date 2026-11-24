"""
URL configuration for regal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', views.health, name='health'),
    path('tasks/run/', views.scheduled_tasks, name='scheduled_tasks'),
    path('account/', include('accounts.urls')),
    path('staff/bookings/', include('bookings.staff_urls')),
    path('staff/accounts/', include('accounts.staff_urls')),
    path('staff/venue/', include('venue.staff_urls')),
    path('staff/', include('staff.urls')),
    path('', include('bookings.urls')),
    path('', include('screenings.urls')),
]
