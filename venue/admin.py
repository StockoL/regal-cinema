from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import VenueSettings


@admin.register(VenueSettings)
class VenueSettingsAdmin(admin.ModelAdmin):
    """The one row of venue settings (4.23). Changing it needs its own
    permission, and there's never a second row to add or one to
    delete. Pausing online sales has its own page, which asks why and
    logs it, so here it's only shown."""

    exclude = ['online_sales_paused']
    readonly_fields = ['online_sales']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('venue.manage_venue_settings')

    @admin.display(description='Online sales')
    def online_sales(self, venue):
        return format_html(
            '{}. <a href="{}">Pause or resume them on their own page</a>, '
            'which asks why and logs it.',
            'Paused' if venue.online_sales_paused else 'On',
            reverse('venue_staff:online_sales'),
        )
