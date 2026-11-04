from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet

from .models import (
    Film,
    Screen,
    Screening,
    ScreeningClosedArea,
    ScreeningPrice,
    Seat,
    SeatingLayout,
    TicketClass,
    TicketType,
)


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ('title', 'age_rating', 'duration_minutes', 'is_active')
    list_filter = ('is_active', 'age_rating')
    search_fields = ('title',)


SEAT_FIELDS = (
    'area', 'row_label', 'number', 'table_number', 'row_index',
    'column_index', 'is_wheelchair_space', 'is_companion_seat', 'is_active',
    'label_override',
)


class FixedSeatInline(admin.TabularInline):
    """Seats that appear in every layout, which is the whole circle.
    Stalls seats are edited on their layout's page."""

    model = Seat
    fields = SEAT_FIELDS
    extra = 0
    verbose_name = 'fixed seat'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(layout__isnull=True)


class SeatingLayoutInline(admin.TabularInline):
    model = SeatingLayout
    fields = ('name', 'is_default')
    extra = 0
    show_change_link = True


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'is_active')
    inlines = [SeatingLayoutInline, FixedSeatInline]


class LayoutSeatFormSet(BaseInlineFormSet):
    """A seat belongs to its layout's screen, so the form doesn't ask."""

    def save_new(self, form, commit=True):
        form.instance.screen = self.instance.screen
        return super().save_new(form, commit=commit)

    def clean(self):
        super().clean()
        # Every stalls layout needs a wheelchair space (4.1). The circle
        # can't have one, so a layout is the only place to check.
        seats = [
            form.cleaned_data for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get('DELETE')
        ]
        if seats and not any(
            seat['is_wheelchair_space'] and seat['is_active']
            for seat in seats
        ):
            raise ValidationError(
                'A layout needs at least one wheelchair space in use.'
            )


class LayoutSeatInline(admin.TabularInline):
    model = Seat
    formset = LayoutSeatFormSet
    fields = SEAT_FIELDS
    extra = 0


@admin.register(SeatingLayout)
class SeatingLayoutAdmin(admin.ModelAdmin):
    list_display = ('screen', 'name', 'is_default')
    list_filter = ('screen',)
    inlines = [LayoutSeatInline]


@admin.register(TicketClass)
class TicketClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_price_pence', 'is_active')


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')


class ScreeningPriceInline(admin.TabularInline):
    model = ScreeningPrice
    extra = 0


class ClosedAreaInline(admin.TabularInline):
    model = ScreeningClosedArea
    extra = 0


@admin.register(Screening)
class ScreeningAdmin(admin.ModelAdmin):
    list_display = ('film', 'date_time', 'screen', 'ticket_class',
                    'is_private', 'is_cancelled')
    list_filter = ('screen', 'is_private', 'ticket_class')
    date_hierarchy = 'date_time'
    readonly_fields = ('ends_at',)
    inlines = [ScreeningPriceInline, ClosedAreaInline]

    @admin.display(boolean=True, description='Cancelled')
    def is_cancelled(self, screening):
        return screening.is_cancelled
