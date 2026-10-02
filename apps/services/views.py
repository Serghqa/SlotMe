from django.apps import apps
from apps.core.utils import get_paginated_page
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from apps.core.utils import get_next_url
from .models import Service


Master = apps.get_model('masters', 'Master')


def service_list_view(request):
    """
    Страница со списком услуг.
    """
    services_queryset = Service.objects.filter(is_active=True).order_by('name')
    page = request.GET.get('page', 1)
    services_page = get_paginated_page(services_queryset, page, 5)

    return render(request, 'services/service_list.html', {'services': services_page})


def services_by_master_view(request, master_id):
    """
    Отображает список активных услуг конкретного мастера
    """
    master = get_object_or_404(
        Master,
        id=master_id,
        is_active=True
    )
    services_queryset = master.services.filter(is_active=True).order_by('name')
    page = request.GET.get('page', 1)
    services_page = get_paginated_page(services_queryset, page, 5)

    to_masters_url = get_next_url(request, reverse('masters:master_list'))

    context = {
        'master': master,
        'services': services_page,
        'to_masters_url': to_masters_url,
    }
    return render(request, 'services/master_services.html', context)
