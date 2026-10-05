from django.apps import apps
from django.db import DatabaseError, IntegrityError
from django.contrib import messages
from apps.core.decorators import admin_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from datetime import datetime
from apps.core.choices import StatusChoices
from apps.core.services import invalidate_slots_cache
from apps.core.utils import get_paginated_page, get_next_url


Appointment = apps.get_model('appointments', 'Appointment')
Master = apps.get_model('masters', 'Master')


@admin_required
def master_list_view(request):
    """
    Страница со списком всех мастеров для администратора.
    Показывает активных мастеров, с пагинацией.
    """
    masters_queryset = Master.objects\
        .filter(is_active=True)\
            .order_by('user__first_name')\
                .annotate(services_count=Count('services', filter=~Q(services__is_active=False)))

    page = request.GET.get('page', 1)
    masters_page = get_paginated_page(masters_queryset, page, 3)

    return render(request, 'admin_panel/master_list.html', {'masters': masters_page})


@admin_required
def services_by_master_view(request, master_id):
    """
    Страница со списком всех услуг мастера для администратора.
    """
    master = get_object_or_404(
        Master,
        id=master_id,
        is_active=True
    )
    services_queryset = master.services.filter(is_active=True)
    page = request.GET.get('page', 1)
    services_page = get_paginated_page(services_queryset, page, 5)

    to_masters_url = get_next_url(request, reverse('admin_panel:master_list'))

    context = {
        'master': master,
        'services': services_page,
        'to_masters_url': to_masters_url,
    }
    return render(request, 'admin_panel/master_services.html', context)


@admin_required
@require_POST
def update_appointment_status_view(request, appointment_id):
    """
    Обновление статуса записи.
    """
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
    )

    to_appointments_url = get_next_url(request, reverse('admin_panel:appointment_list'))

    if not appointment.can_be_closed:
        if not appointment.is_past:
            messages.error(request, 'Статус будущей записи менять запрещено.')
        else:
            messages.error(request, 'Запись нельзя изменить.')
        return redirect(to_appointments_url)

    new_status = request.POST.get('status')
    if new_status not in appointment.allowed_status_transitions:
        messages.error(request, f"Нельзя изменить статус на {new_status}.")
        return redirect(to_appointments_url)

    appointment.status = new_status
    try:
        appointment.save()
    except IntegrityError:
        messages.error(request, f"Не удалось обновить статус записи #{appointment.id}. Попробуйте ещё раз."  )
        return redirect(to_appointments_url)
    except DatabaseError:
        messages.error(request, 'Ошибка базы данных. Попробуйте позже.')
        return redirect(to_appointments_url)

    if appointment.is_completed:
        messages.success(request, f"Запись #{appointment.id} отмечена как завершённая.")
    elif appointment.is_no_show:
        messages.warning(request, f"Запись {appointment.id} отмечена как неявка.")

    return redirect(to_appointments_url)


@admin_required
def appointment_list_view(request):
    date_str = request.GET.get('date')
    master_id = request.GET.get('master')
    status = request.GET.get('status')

    valid_stutuses = [s[0] for s in StatusChoices.choices]

    now = timezone.localtime()

    appointments_queryset = Appointment.objects.select_related(
        'client', 'master__user', 'service'
    ).order_by('-start_datetime')

    if date_str:
        try:
            filter_date = datetime.fromisoformat(date_str).date()
            appointments_queryset = appointments_queryset.filter(start_datetime__date=filter_date)
        except ValueError:
            date_str = ''

    if master_id and master_id.isdigit():
        appointments_queryset = appointments_queryset.filter(master_id=master_id)

    if status in valid_stutuses:
        appointments_queryset = appointments_queryset.filter(status=status)
    else:
        status = ''

    page = request.GET.get('page', 1)
    appointments_page = get_paginated_page(appointments_queryset, page, 10)

    # Список мастеров для фильтра
    masters = Master.objects.filter(is_active=True).order_by('user__first_name')

    context = {
        'appointments': appointments_page,
        'masters': masters,
        'selected_date': date_str or '',
        'selected_master': master_id or '',
        'selected_status': status or '',
        'status_choices': StatusChoices.choices,
        'now': now,
    }
    return render(request, 'admin_panel/appointment_list.html', context)


@admin_required
def cancel_appointment_view(request, appointment_id):
    appointment = get_object_or_404(
        Appointment.objects.select_related('master__user'),
        id=appointment_id,
    )

    to_appointments_url = get_next_url(request, reverse('admin_panel:appointment_list'))

    if request.method == 'POST':
        if not appointment.can_be_cancelled:
            if appointment.is_cancelled:
                messages.error(request, 'Запись уже отменена.')
            elif appointment.is_past:
                messages.error(request, 'Нельзя отменить прошедшую или уже начавшуюся запись.')
            else:
                messages.error(request, 'Эту запись нельзя отменить.')
            return redirect(to_appointments_url)

        reason = request.POST.get('reason', '').strip() or 'Отменено администратором'
        appointment.status = StatusChoices.CANCELLED
        appointment.cancel_reason = reason[:500]
        try:
            appointment.save()
        except IntegrityError:
            messages.error(request, 'Не удалось отменить запись. Попробуйте ещё раз.')
            return redirect(to_appointments_url)
        except DatabaseError:
            messages.error(request, 'Ошибка базы данных. Попробуйте позже.')
            return redirect(to_appointments_url)

        invalidate_slots_cache(appointment.master, appointment.start_datetime.date())
        messages.success(
            request,
            f"Запись к мастеру {appointment.master.user.display_name} на "
            f"{appointment.start_datetime:%d.%m.%Y} в {appointment.start_datetime:%H:%M} успешно отменена."
        )

        return redirect(to_appointments_url)

    else:
        context = {
            'appointment': appointment,
            'to_appointments_url': to_appointments_url
        }
        return render(request, 'appointments/cancel_confirm.html', context)
