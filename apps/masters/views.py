from django.apps import apps
from apps.core.decorators import admin_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime
from apps.appointments.services import get_available_slots
from .models import Master


User = apps.get_model('users', 'User')
Service = apps.get_model('services', 'Service')


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


@login_required
@admin_required
def admin_master_list_view(request):
    masters = Master.objects.prefetch_related('services').order_by('user__last_name')
    return render(request, 'masters/admin_list.html', {'masters': masters})


@admin_required
def admin_master_create_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        service_ids = request.POST.getlist('services')

        # Проверки
        if not username:
            messages.error(request, 'Логин обязателен.')
            return redirect('masters:admin_create')

        user = User.objects.filter(username=username).first()
        if not user:
            messages.error(request, 'Пользователя с таким логином не существует.')
            return redirect('masters:admin_create')

        if Master.objects.filter(user=user).exists():
            messages.error(request, 'Такой мастер уже существует.')
            return redirect('masters:admin_create')

        # Создаём профиль мастера
        master = Master.objects.create(user=user)

        # Назначаем услуги
        if service_ids:
            master.services.set(service_ids)

        messages.success(request, f'Мастер {user.get_full_name() or username} создан.')
        return redirect('masters:admin_list')

    services = Service.objects.filter(is_active=True)
    return render(request, 'masters/admin_create.html', {'services': services})


@admin_required
@require_POST
def admin_master_toggle_active_view(request, master_id):
    master = get_object_or_404(Master, id=master_id)

    master.is_active = not master.is_active
    master.save()
    status = 'разблокирован' if master.is_active else 'заблокирован'
    messages.success(request, f'Мастер {master.user.get_full_name() or master.user.username} {status}.')

    return redirect('masters:admin_list')


@admin_required
def admin_master_services(request, master_id):
    master = get_object_or_404(Master, id=master_id)

    if request.method == 'POST':
        selected_service_ids = request.POST.getlist('services')

        master.services.set(selected_service_ids)

        messages.success(request, f"Услуги мастера {master} успешно обновлены.")
        return redirect('masters:admin_list')

    all_services = Service.objects.all()
    return render(request, 'masters/admin_services.html', {
        'master': master,
        'all_services': all_services
    })
