from django.apps import apps
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from apps.core.decorators import master_required
from apps.core.services import invalidate_slots_cache
from apps.core.utils import get_paginated_page, get_url_with_params, get_next_url
from .models import Appointment


Master = apps.get_model('masters', 'Master')


@login_required
def book_appointment_view(request, master_id):
    """
    Представление для записи на приём к мастеру.
    """
    url_kwargs = {'master_id': master_id}
    query_params = {}

    service_id = request.POST.get('service_id')
    date_str = request.POST.get('date')
    time_str = request.POST.get('time')

    if service_id: query_params['service_id'] = service_id
    if date_str: query_params['date'] = date_str

    redirect_url = get_url_with_params('masters:master_detail', url_kwargs, **query_params)

    if request.method != 'POST':
        return redirect(redirect_url)

    if not request.user.is_client:
        messages.error(request, 'Только клиенты могут записываться на приём.')
        return redirect(redirect_url)

    master = get_object_or_404(Master, id=master_id, is_active=True)

    if not service_id:
        messages.error(request, 'Услуга не выбрана.')
        return redirect(redirect_url)

    service = get_object_or_404(master.services, id=service_id, is_active=True)

    # Проверка обязательных полей
    if not date_str or not time_str:
        messages.error(request, 'Выберите дату и время.')
        return redirect(redirect_url)

    # Собираем datetime
    try:
        start_datetime = timezone.make_aware(
            datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
        )
    except ValueError:
        messages.error(request, 'Неверный формат даты или времени.')
        return redirect(redirect_url)

    # Проверка: не в прошлом
    if start_datetime < timezone.now():
        messages.error(request, 'Нельзя записаться на прошедшее время.')
        return redirect(redirect_url)

    # Проверка: слот свободен (без кэша — прямой запрос)
    end_datetime = start_datetime + service.duration

    created = False
    error_message = None
    try:
        with transaction.atomic():
            Master.objects.select_for_update().get(pk=master.pk)
            overlapping = Appointment.objects.filter(
                master=master,
                start_datetime__lt=end_datetime,
                end_datetime__gt=start_datetime,
                status='booked'
            ).exists()

            if not overlapping:
                # Создаём запись
                Appointment.objects.create(
                    client=request.user,
                    master=master,
                    service=service,
                    start_datetime=start_datetime,
                )
                created = True
    except IntegrityError:
        error_message = 'Это время только что заняли. Попробуйте другое.'

    except DatabaseError:
        error_message = 'Ошибка базы данных. Попробуйте позже.'

    # Сбрасываем кэш слотов
    invalidate_slots_cache(master, start_datetime.date())

    if not created:
        messages.error(request, error_message or 'Это время только что заняли. Попробуйте другое.')
        return redirect(redirect_url)

    messages.success(
        request,
        f'Вы записаны к {master.user.display_name} '
        f'на {start_datetime:%d.%m.%Y} в {start_datetime:%H:%M}.'
    )
    return redirect('appointments:client_appointments')


@login_required
def client_appointments_view(request):
    """
    Представление для отображения записей клиента.
    """
    appointments_queryset = Appointment.objects.filter(
        client=request.user
    ).select_related('master__user', 'service').order_by('-start_datetime')

    # Определяем текущую вкладку (по умолчанию 'upcoming')
    tab = request.GET.get('tab', 'upcoming')
    if tab not in ('upcoming', 'past'):
        tab = 'upcoming'
    now = timezone.localtime()

    # Фильтруем данные в зависимости от выбранной вкладки
    if tab == 'past':
        # Прошедшими считаются записи:
        # Либо у них финальный статус (completed, cancelled, no_show)
        # Либо статус все еще 'booked', но время окончания приема (start_datetime + duration) УЖЕ В ПРОШЛОМ
        appointments_queryset = appointments_queryset.filter(
            Q(status__in=['completed', 'cancelled', 'no_show']) |
            Q(status='booked', end_datetime__lt=now)
        )
    else:
        appointments_queryset = appointments_queryset.filter(
            status='booked',
            end_datetime__gte=now
        )

    page = request.GET.get('page', 1)
    appointments_page = get_paginated_page(appointments_queryset, page, 10)

    context = {
        'appointments': appointments_page,
        'current_tab': tab
    }

    return render(request, 'appointments/client_appointments.html', context)


@login_required
def client_cancel_appointment_view(request, appointment_id):
    """
    Представление отмены записи клиентом.
    """
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        client=request.user,
    )
    to_appointments_url = get_next_url(request, reverse('appointments:client_appointments'))

    if not appointment.can_be_cancelled:
        messages.error(request, 'Эту запись нельзя отменить.')
        return redirect(to_appointments_url)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip() or 'Отменено клиентом'
        appointment.status = 'cancelled'
        appointment.cancel_reason = reason[:500]
        appointment.cancelled_at = timezone.now()
        appointment.save()

        # Инвалидация кэша
        invalidate_slots_cache(appointment.master, appointment.start_datetime.date())

        messages.success(
            request,
            f'Запись к мастеру {appointment.master.user.display_name} на '
            f'{appointment.start_datetime:%d.%m.%Y} в {appointment.start_datetime:%H:%M} успешно отменена.'
        )
        return redirect(to_appointments_url)


    context = {
        'appointment': appointment,
        'to_appointments_url': to_appointments_url,
    }
    return render(request, 'appointments/cancel_confirm.html', context)


@master_required
def master_schedule_view(request):
    """
    Представление записей у мастера.
    """
    date_str = request.GET.get('date')
    selected_date = timezone.localdate()
    if date_str:
        try:
            selected_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            selected_date = timezone.localdate()
            date_str = selected_date.isoformat()
    else:
        date_str = selected_date.isoformat()

    # --- РАСЧЕТ ДАННЫХ ДЛЯ КНОПОК ---
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)

    master = request.user.master_profile

    appointments_queryset = Appointment.objects.filter(
        master=master,
        start_datetime__date=selected_date,
    ).select_related('client', 'service').order_by('start_datetime')
    page = request.GET.get('page', 1)
    appointments = get_paginated_page(appointments_queryset, page, 10)

    context = {
        'appointments': appointments,
        'selected_date': selected_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'raw_date_str': date_str,
    }
    return render(request, 'appointments/master_schedule.html', context)
