from django.shortcuts import render
from apps.appointments.services import get_paginated_page
from .models import Service


def service_list_view(request):
    services_queryset = Service.objects.filter(is_active=True).order_by('price')
    page = request.GET.get('page', 1)
    services_page = get_paginated_page(services_queryset, page, 5)

    return render(request, 'services/service_list.html', {'services': services_page, 'role': 'client'})
