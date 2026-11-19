from django.contrib import admin, messages

from .models import Booking
from .services import SeatsLost, confirm_booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'screening', 'status', 'seat_count',
                    'paid_at')
    list_filter = ('status',)
    search_fields = ('reference',)
    readonly_fields = ('reference', 'paid_at')
    actions = ['mark_paid']

    @admin.action(description='Mark as paid')
    def mark_paid(self, request, queryset):
        """Stands in for Stripe's webhook until payments are built, and
        goes through the same confirm_booking (4.32)."""
        for booking in queryset:
            try:
                confirm_booking(booking)
            except SeatsLost:
                self.message_user(
                    request,
                    f"{booking.reference} lost a seat, so it wasn't paid.",
                    messages.ERROR,
                )
