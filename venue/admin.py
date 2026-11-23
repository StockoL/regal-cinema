from django.contrib import admin

from .models import VenueSettings


@admin.register(VenueSettings)
class VenueSettingsAdmin(admin.ModelAdmin):
    """The one row of venue settings (4.23). Changing it needs its own
    permission, and there's never a second row to add or one to
    delete."""

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('venue.manage_venue_settings')
