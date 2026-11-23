from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'screening', 'status', 'seat_count',
                    'paid_at')
    list_filter = ('status',)
    search_fields = ('reference',)
    readonly_fields = ('reference', 'paid_at')
