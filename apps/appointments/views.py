from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from datetime import datetime
from apps.masters.models import Master
from apps.services.models import Service
from .models import Appointment
from .services import get_available_slots, invalidate_slots_cache


@login_required
def book_appointment_view(request, master_id):
    if request.method != 'POST':
        return redirect('masters:master_detail', master_id=master_id)

    master = get_object_or_404(Master, id=master_id, is_active=True)
    service_id = request.POST.get('service_id')
    service = get_object_or_404(master.services, id=service_id, is_active=True)
    date_str = request.POST.get('date')
    time_str = request.POST.get('time')

    # Проверка обязательных полей
    if not date_str or not time_str:
        messages.error(request, 'Выберите дату и время.')
        return redirect('masters:master_detail', master_id=master_id)

    # Собираем datetime
    try:
        start_datetime = timezone.make_aware(
            datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
        )
    except ValueError:
        messages.error(request, 'Неверный формат даты или времени.')
        return redirect('masters:master_detail', master_id=master_id)

    # Проверка: не в прошлом
    if start_datetime < timezone.localtime():
        messages.error(request, 'Нельзя записаться на прошедшее время.')
        return redirect('masters:master_detail', master_id=master_id)

    # Проверка: слот свободен (без кэша — прямой запрос)
    end_datetime = start_datetime + service.duration

    with transaction.atomic():
        overlapping = Appointment.objects.filter(
            master=master,
            start_datetime__lt=end_datetime,
            end_datetime__gt=start_datetime,
            status='booked'
        ).exists()

        if overlapping:
            messages.error(request, 'Это время только что заняли. Выберите другое время.')
            invalidate_slots_cache(master, start_datetime.date())
            return redirect('masters:master_detail', master_id=master_id)

        # Создаём запись
        appointment = Appointment.objects.create(
            client=request.user,
            master=master,
            service=service,
            start_datetime=start_datetime,
        )

    # Сбрасываем кэш слотов
    invalidate_slots_cache(master, start_datetime.date())

    master_name = master.user.get_full_name() or master.user.username
    messages.success(
        request,
        f'Вы записаны к {master_name} '
        f'на {start_datetime:%d.%m.%Y} в {start_datetime:%H:%M}.'
    )
    return redirect('appointments:client_list')


@login_required
def client_appointments_view(request):
    appointments = Appointment.objects.filter(
        client=request.user
    ).select_related('master__user', 'service').order_by('-start_datetime')
    return render(request, 'appointments/client_list.html', {'appointments': appointments})