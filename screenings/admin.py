from django.contrib import admin

from .models import (
    Film,
    Screen,
    Screening,
    ScreeningPrice,
    Seat,
    TicketClass,
    TicketType,
)


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ('title', 'age_rating', 'duration_minutes', 'is_active')
    list_filter = ('is_active', 'age_rating')
    search_fields = ('title',)


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'is_active')
    inlines = [SeatInline]


@admin.register(TicketClass)
class TicketClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_price_pence', 'is_active')


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')


class ScreeningPriceInline(admin.TabularInline):
    model = ScreeningPrice
    extra = 0


@admin.register(Screening)
class ScreeningAdmin(admin.ModelAdmin):
    list_display = ('film', 'date_time', 'screen', 'ticket_class',
                    'is_private', 'is_cancelled')
    list_filter = ('screen', 'is_private', 'ticket_class')
    date_hierarchy = 'date_time'
    readonly_fields = ('ends_at',)
    inlines = [ScreeningPriceInline]

    @admin.display(boolean=True, description='Cancelled')
    def is_cancelled(self, screening):
        return screening.is_cancelled
