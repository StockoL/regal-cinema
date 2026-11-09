from django.shortcuts import get_object_or_404, render

from screenings.models import Screening


def screening_seats(request, pk):
    """Choosing seats for one screening (journey 2). A private screening
    isn't found; a cancelled one says so plainly (4.11, 4.19)."""
    screening = get_object_or_404(
        Screening.objects.select_related('film', 'screen'),
        pk=pk, is_private=False, film__is_active=True,
    )
    if screening.is_cancelled:
        return render(request, 'bookings/screening_cancelled.html',
                      {'screening': screening}, status=410)
    return render(request, 'bookings/screening_seats.html', {
        'screening': screening,
    })
