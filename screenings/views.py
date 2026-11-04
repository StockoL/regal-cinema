from datetime import date, timedelta

from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Film, Screening

# How many days the date strip offers, starting today.
DAYS_SHOWN = 7


def chosen_day(request, days):
    """The day in ?date=, or today if it's missing, malformed or not one
    of the days on offer."""
    try:
        day = date.fromisoformat(request.GET.get('date', ''))
    except ValueError:
        return days[0]
    return day if day in days else days[0]


def screening_list(request):
    """The home page: one day's public screenings, grouped by film, in
    the order each film first shows that day (journey 1)."""
    today = timezone.localdate()
    days = [today + timedelta(days=n) for n in range(DAYS_SHOWN)]
    day = chosen_day(request, days)
    screenings = (
        Screening.objects.public().on_date(day)
        .select_related('film').order_by('date_time')
    )
    films = {}
    for screening in screenings:
        films.setdefault(screening.film, []).append(screening)
    return render(request, 'screenings/screening_list.html', {
        'day': day,
        'days': days,
        'listings': list(films.items()),
    })


def film_detail(request, slug):
    """A film's own page. A retired film is gone from the public site."""
    film = get_object_or_404(Film, slug=slug, is_active=True)
    return render(request, 'screenings/film_detail.html', {'film': film})
