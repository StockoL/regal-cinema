import hmac
import logging
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_safe

logger = logging.getLogger(__name__)


@require_safe
def health(request):
    """Answer the uptime ping without touching the database, so the ping
    wakes Render's web service but not Neon's database."""
    return HttpResponse('ok', content_type='text/plain')


@csrf_exempt
@require_POST
def scheduled_tasks(request):
    """Run the scheduled work when cron-job.org calls (4.32). It needs
    the token from the environment as a bearer token, and with no token
    set nothing can run it. Each command is safe to run twice. What
    they report is logged and sent back."""
    token = settings.SCHEDULED_TASK_TOKEN
    given = request.headers.get('Authorization', '').removeprefix('Bearer ')
    if not token or not hmac.compare_digest(given, token):
        return HttpResponseForbidden()
    out = StringIO()
    call_command('reconcile_pending', stdout=out)
    logger.info('Scheduled tasks: %s', out.getvalue().strip())
    return HttpResponse(out.getvalue(), content_type='text/plain')
