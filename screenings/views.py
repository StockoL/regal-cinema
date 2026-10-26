from django.shortcuts import render


def screening_list(request):
    """The home page: what's on. Listings come with journey 1."""
    return render(request, 'screenings/screening_list.html')
