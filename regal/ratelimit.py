"""Slowing down repeated attempts at the forms people might abuse
(architecture 4.29): logging in, registering, resetting a password and
holding seats. Counts live in the shared database cache, so both
workers agree, and they're kept under a hash of the visitor's address,
never the address itself, so nothing is tracked about anyone."""

import hashlib
from functools import wraps

from django.core.cache import caches
from django.shortcuts import render


def client_address(request):
    """Behind Render's proxy the visitor's address is the first one in
    X-Forwarded-For."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() or request.META.get(
        'REMOTE_ADDR', ''
    )


def over_limit(request, action, limit, window):
    """Count one more attempt at an action, and say whether this visitor
    has now gone over the limit for the window, in seconds."""
    visitor = hashlib.sha256(client_address(request).encode()).hexdigest()
    key = f'ratelimit:{action}:{visitor}'
    cache = caches['ratelimit']
    if cache.add(key, 1, window):
        return False
    try:
        return cache.incr(key) > limit
    except ValueError:
        # It expired between the two calls: this attempt starts afresh.
        cache.set(key, 1, window)
        return False


def rate_limit(action, limit, window):
    """Allow a view's form to be sent this many times per window. One
    more gets a plain page with a one-line message and a 429 status."""
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method == 'POST' and over_limit(request, action,
                                                       limit, window):
                return render(request, '429.html', status=429)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
