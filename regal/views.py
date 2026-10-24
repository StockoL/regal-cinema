from django.http import HttpResponse
from django.views.decorators.http import require_safe


@require_safe
def health(request):
    """Answer the uptime ping without touching the database, so the ping
    wakes Render's web service but not Neon's database."""
    return HttpResponse('ok', content_type='text/plain')
