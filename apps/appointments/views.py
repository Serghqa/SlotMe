from django.apps import apps
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.http import urlencode
from django.urls import reverse
from apps.core.decorators import master_required, admin_required
from datetime import datetime, timedelta
from .models import Appointment
from .services import invalidate_slots_cache


Master = apps.get_model('masters', 'Master')


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
    if start_datetime < timezone.now():
        messages.error(request, 'Нельзя записаться на прошедшее время.')
        return redirect('masters:master_detail', master_id=master_id)

    # Проверка: слот свободен (без кэша — прямой запрос)
    end_datetime = start_datetime + service.duration

    try:
        with transaction.atomic():
            overlapping = Appointment.objects.select_for_update().filter(
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
    except Exception:
        invalidate_slots_cache(master, start_datetime.date())
        messages.error(request, 'Не удалось создать запись. Попробуйте снова.')
        return redirect('masters:master_detail', master_id=master_id)

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
    queryset = Appointment.objects.filter(
        client=request.user
    ).select_related('master__user', 'service').order_by('-start_datetime')

    # Определяем текущую вкладку (по умолчанию 'upcoming')
    tab = request.GET.get('tab', 'upcoming')
    now = timezone.localtime()

    # Фильтруем данные в зависимости от выбранной вкладки
    if tab == 'past':
        # Прошедшими считаются записи:
        # Либо у них финальный статус (completed, cancelled, no_show)
        # Либо статус все еще 'booked', но время окончания приема (start_datetime + duration) УЖЕ В ПРОШЛОМ
        appointments_list = queryset.filter(
            Q(status__in=['completed', 'cancelled', 'no_show']) |
            Q(status='booked', end_datetime__lt=now)
        )
    else:
        appointments_list = queryset.filter(
            status='booked',
            start_datetime__gte=now
        )
    # Пагинация: показываем по 10 записей на одной странице
    paginator = Paginator(appointments_list, 10)
    page = request.GET.get('page')

    try:
        appointments = paginator.page(page)
    except PageNotAnInteger:
        appointments = paginator.page(1)
    except EmptyPage:
        appointments = paginator.page(paginator.num_pages)

    context = {
        'appointments': appointments,
        'current_tab': tab
    }

    return render(request, 'appointments/client_list.html', context)


@login_required
def client_cancel_appointment_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        client=request.user,
        status='booked'
    )

    if not appointment.can_be_cancelled:
        if appointment.is_past:
            messages.error(request, 'Нельзя отменить прошедшую запись.')
        else:
            messages.error(request, 'Можно отменить только активную (забронированную) запись.')
        return redirect('appointments:client_list')

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            reason = 'Отменено клиентом'
        else:
            reason = reason[:500]
        appointment.status = 'cancelled'
        appointment.cancel_reason = reason
        appointment.save()

        # Инвалидация кэша
        invalidate_slots_cache(appointment.master, appointment.start_datetime.date())

        messages.success(request, f'Запись #{appointment.id} успешно отменена.')
        return redirect('appointments:client_list')

    return render(request, 'appointments/cancel_confirm.html', {'appointment': appointment, 'role': 'client'})


@master_required
def master_cancel_appointment_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('master'),
        id=appointment_id,
        master=request.user.master_profile,
        status='booked'
    )

    selected_date = appointment.start_datetime.date()

    if not appointment.can_be_cancelled:
        if appointment.is_past:
            messages.error(request, 'Нельзя отменить прошедшую запись.')
        else:
            messages.error(request, 'Можно отменить только активную (забронированную) запись.')
        return redirect(f"{reverse('appointments:master_schedule')}?date={selected_date}")

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            reason = 'Отменено мастером'
        else:
            reason = reason[:500]

        appointment.status = 'cancelled'
        appointment.cancel_reason = reason
        appointment.save()

        invalidate_slots_cache(appointment.master, selected_date)

        messages.success(request, f'Запись #{appointment.id} успешно отменена.')
        return redirect(f"{reverse('appointments:master_schedule')}?date={selected_date}")

    return render(request, 'appointments/cancel_confirm.html', {'appointment': appointment, 'role': 'master'})


@master_required
def master_schedule_view(request):
    date_str = request.GET.get('date')
    selected_date = timezone.localdate()
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    master = request.user.master_profile

    appointments = Appointment.objects.filter(
        master=master,
        start_datetime__date=selected_date,
        # status='booked'
    ).select_related('client', 'service').order_by('start_datetime')

    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    now = timezone.localtime()

    context = {
        'appointments': appointments,
        'selected_date': selected_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'now': now
    }
    return render(request, 'appointments/master_schedule.html', context)


@master_required
@require_POST
def master_update_appointment_status_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        master=request.user.master_profile,
        status='booked'
    )
    selected_date = appointment.start_datetime.date()
    if appointment.start_datetime > timezone.now():
        messages.error(request, 'Нельзя изменить статус будущей записи.')
        return redirect(f"{reverse('appointments:master_schedule')}?date={selected_date}")

    new_status = request.POST.get('status')
    if new_status in ['completed', 'no_show']:
        appointment.status = new_status
        appointment.save()
        if new_status == 'completed':
            messages.success(request, 'Запись отмечена как завершённая.')
        elif new_status == 'no_show':
            messages.warning(request, 'Запись отмечена как неявка.')
    else:
        messages.error(request, 'Неверный статус.')


    return redirect(f"{reverse('appointments:master_schedule')}?date={selected_date}")


@admin_required
@require_POST
def admin_update_appointment_status_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        status='booked'
    )
    redirect_url = reverse('appointments:admin_list')
    query_params = request.GET.dict()
    if query_params:
        redirect_url = f"{redirect_url}?{urlencode(query_params)}"

    selected_date = appointment.start_datetime.date()
    if appointment.start_datetime > timezone.now():
        messages.error(request, 'Нельзя изменить статус будущей записи.')
        return redirect(f"{redirect_url}?date={selected_date}")

    new_status = request.POST.get('status')
    if new_status in ['completed', 'no_show']:
        appointment.status = new_status
        appointment.save()
        if new_status == 'completed':
            messages.success(request, 'Запись отмечена как завершённая.')
        elif new_status == 'no_show':
            messages.warning(request, 'Запись отмечена как неявка.')
    else:
        messages.error(request, 'Неверный статус.')

    return redirect(redirect_url)


@admin_required
def admin_appointments_view(request):
    date_str = request.GET.get('date')
    master_id = request.GET.get('master')
    status = request.GET.get('status')
    now = timezone.localtime()

    appointments = Appointment.objects.select_related(
        'client', 'master__user', 'service'
    ).order_by('-start_datetime')

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            appointments = appointments.filter(start_datetime__date=filter_date)
        except ValueError:
            date_str = ''

    if master_id and master_id.isdigit():
        appointments = appointments.filter(master_id=master_id)

    if status:
        appointments = appointments.filter(status=status)

    # Список мастеров для фильтра
    masters = Master.objects.filter(is_active=True)

    context = {
        'appointments': appointments,
        'masters': masters,
        'selected_date': date_str or '',
        'selected_master': master_id or '',
        'selected_status': status or '',
        'status_choices': Appointment.STATUS_CHOICES,
        'now': now,
    }
    return render(request, 'appointments/admin_list.html', context)


@admin_required
def admin_cancel_appointment_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('master'),
        id=appointment_id,
        status='booked'
    )
    redirect_url = reverse('appointments:admin_list')
    query_params = request.GET.dict()
    if query_params:
        redirect_url = f"{redirect_url}?{urlencode(query_params)}"

    if request.method == 'POST':
        if not appointment.can_be_cancelled:
            if appointment.is_past:
                messages.error(request, 'Нельзя отменить прошедшую запись.')
            else:
                messages.error(request, 'Можно отменить только активную (забронированную) запись.')
            return redirect(redirect_url)

        reason = request.POST.get('reason', '').strip()
        if not reason:
            reason = 'Отменено администратором'
        else:
            reason = reason[:500]
        appointment.status = 'cancelled'
        appointment.cancel_reason = reason
        appointment.save()

        invalidate_slots_cache(appointment.master, appointment.start_datetime.date())
        messages.success(request, f'Запись #{appointment.id} отменена.')

        return redirect(redirect_url)

    return render(request, 'appointments/cancel_confirm.html', {'appointment': appointment, 'role': 'admin', 'query_string': request.GET.urlencode()})
