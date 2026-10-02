from django.apps import apps
from django.db.models import Count, Prefetch, Q
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.urls import reverse
from datetime import datetime
from apps.core.utils import get_paginated_page, get_next_url
from apps.core.services import get_available_slots
from .models import Master


Service = apps.get_model('services', 'Service')


def master_list_view(request):
    """
    Страница со списком всех мастеров.
    """
    active_services_prefetch = Prefetch(
        'services',
        queryset=Service.objects.filter(is_active=True).order_by('name'),
    )
    masters_queryset = Master.objects.filter(is_active=True)\
        .annotate(active_services_count=Count('services', filter=Q(services__is_active=True)))\
            .prefetch_related(active_services_prefetch)\
                .order_by('user__first_name')
    page = request.GET.get('page', 1)
    masters_page = get_paginated_page(masters_queryset, page, 5)

    return render(request, 'masters/master_list.html', {'masters': masters_page})


def master_detail_view(request, master_id):
    """
    Страница для записи к мастеру с детальной информацией.
    """
    master = get_object_or_404(
        Master,
        id=master_id,
        is_active=True
    )

    services = master.services.filter(is_active=True).order_by('name')
    date_str = request.GET.get('date')
    service_id = request.GET.get('service_id')

    slots = []
    selected_date = timezone.localdate()
    selected_service = None

    if date_str:
        try:
            selected_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            selected_date = timezone.localdate()
            date_str = selected_date.isoformat()
    else:
        date_str = selected_date.isoformat()

    if service_id:
        selected_service = get_object_or_404(services, id=service_id)

    today = timezone.localdate()
    if selected_service:
        if selected_date >= today:
            slots = get_available_slots(master, selected_date, selected_service)

    context = {
        'master': master,
        'services': services,
        'selected_date': selected_date,
        'selected_service': selected_service,
        'slots': slots,
        'today': today,
        'raw_date_str': date_str,
    }
    return render(request, 'masters/master_detail.html', context)


def masters_by_service_view(request, service_id):
    """
    Представление списка всех мастеров, которые предоставляют конкретную услугу.
    """
    active_services_prefetch = Prefetch(
        'services',
        queryset=Service.objects.filter(is_active=True).order_by('name'),
    )
    service = get_object_or_404(
        Service,
        id=service_id,
        is_active=True
    )
    masters_ids = Master.objects.filter(is_active=True, services__id=service_id).values_list('id', flat=True)
    masters_queryset = Master.objects.filter(id__in=masters_ids)\
        .annotate(active_services_count=Count('services', filter=Q(services__is_active=True)))\
            .prefetch_related(active_services_prefetch)\
                .order_by('user__first_name')
    page = request.GET.get('page', 1)
    masters_page = get_paginated_page(masters_queryset, page, 2)

    to_services_url = get_next_url(request, reverse('services:service_list'))

    context = {
        'masters': masters_page,
        'selected_service': service,
        'to_services_url': to_services_url,
    }

    return render(request, 'masters/master_list.html', context)
