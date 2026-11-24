from django.utils.functional import SimpleLazyObject

from .models import get_settings


def venue(request):
    """The venue settings for any template, such as the footer's phone
    number (4.23). Read only when a template uses them, and a view that
    already read them passes its own, so they aren't read twice."""
    return {'venue': SimpleLazyObject(get_settings)}
