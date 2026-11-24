from django.contrib import messages
from django.shortcuts import redirect, render

from staff.views import staff_permission_required

from .models import get_settings
from .services import set_online_sales_paused


@staff_permission_required('venue.pause_online_sales')
def online_sales(request):
    """Pause or resume online sales, saying why (4.23). The form says
    which it asks for, so a second click finds it done and changes
    nothing."""
    error = None
    if request.method == 'POST':
        paused = request.POST.get('paused') == '1'
        reason = request.POST.get('reason', '').strip()
        if not reason:
            error = 'Say why, so the log explains it later.'
        else:
            state = 'paused' if paused else 'on'
            if set_online_sales_paused(paused, request.user, reason):
                messages.success(request, f'Online sales are now {state}.')
            else:
                messages.info(request, f'Online sales were already {state}.')
            return redirect('venue_staff:online_sales')
    return render(request, 'venue/staff/online_sales.html', {
        'venue': get_settings(), 'error': error,
    })
