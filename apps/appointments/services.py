from datetime import datetime, time, date, timedelta
from django.db.models.functions import Cast
from django.db.models import DateTimeField
from django.core.cache import cache
from django.utils import timezone
from apps.masters.models import Master, WorkSchedule, ScheduleException
from apps.services.models import Service
from .models import Appointment


def get_available_slots(master: Master, date: date, service: Service):
    """
    Возвращает список объектов datetime.time — доступное время начала услуги
    для конкретного мастера на конкретную дату.
    """
    cache_key = f"slots_{master.pk}_{date}_{service.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 1. Проверяем исключения на дату (отпуск, особый день)
    exception = ScheduleException.objects.filter(master=master, date=date).first()
    if exception:
        if not exception.is_working:
            cache.set(cache_key, [], 60)
            return []
        start_time = exception.start_time
        end_time = exception.end_time
    else:
        # 2. Обычное расписание по дню недели
        schedule = WorkSchedule.objects.filter(
            master=master,
            day_of_week=date.weekday(),
            is_working=True
        ).first()
        if not schedule:
            cache.set(cache_key, [], 60)
            return []
        start_time = schedule.start_time
        end_time = schedule.end_time

    # 3. Получаем занятые интервалы
    busy_queryset = Appointment.objects.filter(
        master=master,
        start_datetime__date=date,
        status='booked'
    ).annotate(
        local_start_dt=Cast('start_datetime', DateTimeField()),
        local_end_dt=Cast('end_datetime', DateTimeField())
    ).values_list('local_start_dt', 'local_end_dt')

    # 4. Генерируем свободные слоты с шагом 30 минут
    slots = []
    start_local_datetime = timezone.make_aware(datetime.combine(date, start_time))
    end_local_datetime = timezone.make_aware(datetime.combine(date, end_time))
    now_local_datetime = timezone.localtime()
    if date == now_local_datetime.date():
        if start_local_datetime < now_local_datetime:
            minutes_to_add = 30 - (now_local_datetime.minute % 30)
            start_local_datetime = now_local_datetime + timedelta(minutes=minutes_to_add) - \
                timedelta(seconds=now_local_datetime.second, microseconds=now_local_datetime.microsecond)

    duration = service.duration  # timedelta из DurationField
    current = start_local_datetime
    step = timedelta(minutes=30)

    while current + duration <= end_local_datetime:
        slot_end = current + duration
        if not _is_overlapping(current, slot_end, busy_queryset):
            slots.append(current.time())
        current += step

    cache.set(cache_key, slots, 60)
    return slots


def _is_overlapping(start_local: datetime, end_local: datetime, busy_slots):
    """Проверяет, пересекается ли интервал с занятыми слотами."""
    for start_local_busy, end_local_busy in busy_slots:
        if start_local < end_local_busy and end_local > start_local_busy:
            return True
    return False


def invalidate_slots_cache(master, date):
    """Сбрасывает кэш слотов мастера на конкретную дату."""
    for service in master.services.all():
        cache_key = f"slots_{master.id}_{date}_{service.id}"
        cache.delete(cache_key)
