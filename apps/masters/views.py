from django.apps import apps
from apps.core.decorators import admin_required
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.http import urlencode
from django.urls import reverse
from datetime import datetime
from apps.appointments.services import get_available_slots, get_paginated_page
from .models import Master


User = apps.get_model('users', 'User')
Service = apps.get_model('services', 'Service')


def master_list_view(request):
    masters_queryset = Master.objects.filter(is_active=True).prefetch_related('services').order_by('user__first_name')
    page = request.GET.get('page', 1)
    masters_page = get_paginated_page(masters_queryset, page, 5)

    return render(request, 'masters/master_list.html', {'masters': masters_page})


def master_service_list_view(request, service_id):
    service = get_object_or_404(
        Service.objects.prefetch_related('masters'),
        id=service_id,
        is_active=True
    )
    masters = service.masters.filter(is_active=True).prefetch_related('services')
    back_services_url = request.META.get('HTTP_REFERER', reverse('services:service_list'))
    context = {
        'masters': masters,
        'selected_service': service,
        'back_services_url': back_services_url,
    }

    return render(request, 'masters/master_list.html', context)


def master_detail_view(request, master_id):
    master = get_object_or_404(
        Master.objects.prefetch_related('services'),
        id=master_id,
        is_active=True
    )

    services = master.services.filter(is_active=True)
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
    else:
        date_str = selected_date.isoformat()

    if service_id:
        selected_service = get_object_or_404(services, id=service_id)

    # Считаем слоты только при наличии обоих параметров
    today = timezone.localdate()
    if selected_date and selected_service:
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


@admin_required
def admin_master_list_view(request):
    masters_queryset = Master.objects.prefetch_related('services')\
        .order_by('user__first_name')\
            .annotate(services_count=Count('services'))

    page = request.GET.get('page', 1)
    masters_page = get_paginated_page(masters_queryset, page, 2)

    return render(request, 'masters/admin_list.html', {'masters': masters_page})


@admin_required
def admin_master_services(request, master_id):
    master = get_object_or_404(
        Master.objects.prefetch_related('services'),
        id=master_id,
        is_active=True
    )
    services_queryset = master.services.filter(is_active=True)
    page = request.GET.get('page', 1)
    services_page = get_paginated_page(services_queryset, page, 5)

    redirect_to = request.GET.get('next') or reverse('masters:admin_list')

    context = {
        'master': master,
        'services': services_page,
        'back_masters_url': redirect_to,
        'role': 'admin',
    }
    return render(request, 'services/service_list.html', context)
