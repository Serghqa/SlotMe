from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import datetime
from .models import Master
from apps.appointments.services import get_available_slots


def master_list_view(request):
    masters = Master.objects.filter(is_active=True).prefetch_related('services')
    return render(request, 'masters/master_list.html', {'masters': masters})


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
    selected_date = None
    selected_service = None

    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date_str = None

    if service_id:
        selected_service = get_object_or_404(services, id=service_id)

    # Считаем слоты только при наличии обоих параметров
    if selected_date and selected_service:
        if selected_date >= timezone.localdate():
            slots = get_available_slots(master, selected_date, selected_service)

    context = {
        'master': master,
        'services': services,
        'selected_date': selected_date,
        'selected_service': selected_service,
        'slots': slots,
        'today': timezone.localdate(),
        'raw_date_str': date_str,
    }
    return render(request, 'masters/master_detail.html', context)
