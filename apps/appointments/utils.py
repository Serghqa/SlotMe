from django.apps import apps
from django.utils import timezone
from django.core.exceptions import ValidationError


class AppointmentValidationMixin:
    """Миксин для комплексной валидации Appointment"""

    def clean_appointment(self):
        AppointmentModel = apps.get_model('appointments', 'Appointment')

        status_labels = dict(AppointmentModel.STATUS_CHOICES)
        errors = {}

        if not self.master_id or not self.service_id or not self.client_id or not self.start_datetime:
            raise ValidationError('Заполните обязательные поля.')

        if not self.pk:
            self._validate_master(errors)
            self._validate_service(errors)
            self._validate_master_service(errors)
            self._validate_status_create(errors, status_labels)
            self._validate_not_past_time(errors)
            if 'start_datetime' not in errors:
                self._validate_master_time_availability(errors, AppointmentModel)
        else:
            self._validate_status_update(errors, status_labels, AppointmentModel)

        if errors:
            raise ValidationError(errors)

    def _add_error(self, errors: dict, field_error: str, text_error: str):
        errors.setdefault(field_error, []).append(text_error)

    def _validate_service(self, errors):
        if not self.service.is_active:
            self._add_error(
                errors=errors,
                field_error='service',
                text_error=f'Услуга "{self.service}" неактивна.'
            )

    def _validate_master(self, errors):
        if not self.master.is_active:
            self._add_error(
                errors=errors,
                field_error='master',
                text_error=f'Мастер "{self.master}" неактивен.',
            )

    def _validate_master_service(self, errors):
        if not self.master.services.filter(id=self.service_id).exists():
            self._add_error(
                errors=errors,
                field_error='service',
                text_error=f'Мастер {self.master} не предоставляет услугу "{self.service}".',
            )

    def _validate_status_create(self, errors, status_labels):
        if self.status != 'booked':
            self._add_error(
                errors=errors,
                field_error='status',
                text_error=f'Новая запись может быть только в статусе {status_labels["booked"]}.',
            )

    def _validate_not_past_time(self, errors):
        start_local = timezone.localtime(self.start_datetime)
        now_local = timezone.localtime()
        if start_local < now_local:
            self._add_error(
                errors=errors,
                field_error='start_datetime',
                text_error='Нельзя создать запись на прошедшее время.',
            )

    def _validate_status_update(self, errors, status_labels, appontment_model):
        now = timezone.localtime()
        start_local = timezone.localtime(self.start_datetime)
        # Для существующей записи проверяем переходы
        old_status = appontment_model.objects.only('status').get(pk=self.pk).status

        # Нельзя менять статус завершённой или отменённой записи
        if old_status in ['completed', 'cancelled', 'no_show']:
            if old_status != self.status:
                text_error = (
                    f'Нельзя изменить статус с "{status_labels[old_status]}" на "{status_labels[self.status]}". '
                    f'Запись уже завершена или отменена.'
                )
                self._add_error(
                    errors=errors,
                    field_error='status',
                    text_error=text_error,
                )
            return

        # Запрещаем 'completed' и 'no_show' для будущих записей
        if self.status in ['completed', 'no_show'] and start_local > now:
            text_error = (
                f'Нельзя установить статус "{status_labels[self.status]}" '
                f'для будущей записи ({start_local:%d.%m.%Y %H:%M}).'
            )
            self._add_error(
                errors=errors,
                field_error='status',
                text_error=text_error,
            )
            return

        # 'completed' можно поставить только после времени окончания
        if self.status == 'completed':
            end_local = timezone.localtime(start_local + self.service.duration)
            if now < end_local:
                text_error = (
                    f'Статус {status_labels[self.status]} можно установить только после окончания записи '
                    f'({end_local:%d.%m.%Y %H:%M}).'
                )
                self._add_error(
                    errors=errors,
                    field_error='status',
                    text_error=text_error,
                )

    def _validate_master_time_availability(self, errors, appontment_model):
        start_local = timezone.localtime(self.start_datetime)
        end = self.start_datetime + self.service.duration
        end_local = timezone.localtime(end)

        booking_date = start_local.date()
        booking_start_time = start_local.time()
        booking_end_time = end_local.time()

        # Проверка 1: График работы (Исключения имеют приоритет над базовым расписанием)
        exception = self.master.exceptions.filter(date=booking_date).first()
        work_start, work_end = None, None
        reason = None

        if exception:
            if not exception.is_working:
                reason = exception.reason or 'Выходной'
                self._add_error(
                    errors=errors,
                    field_error='start_datetime',
                    text_error=f'{booking_date:%d.%m.%Y} - мастер не работает. Причина: {reason}',
                )
                return
            reason = exception.reason or 'Особые часы'
            work_start, work_end = exception.start_time, exception.end_time # Получаем особые часы для этого дня
        else:
            # Если исключений нет, ищем регулярный график на этот день недели
            day_of_week = booking_date.weekday()
            schedule = self.master.schedule.filter(day_of_week=day_of_week).first()

            if not schedule or not schedule.is_working:
                self._add_error(
                    errors=errors,
                    field_error='start_datetime',
                    text_error=f'{booking_date:%d.%m.%Y} ({booking_date:%A}) — нерабочий день.',
                )
                return
            work_start, work_end = schedule.start_time, schedule.end_time

        # Проверяем, укладывается ли запись в рабочие часы (учитывая пустые значения)
        if not work_start or not work_end:
            self._add_error(
                errors=errors,
                field_error='start_datetime',
                text_error='Для этого дня у мастера не настроены рабочие часы.',
            )
            return

        if not (work_start <= booking_start_time and work_end >= booking_end_time):
            text_error = (
                f'Запись выходит за рамки рабочего времени мастера в этот день ({work_start:%H:%M} – {work_end:%H:%M}).'
                f' {reason if reason else "Нерабочие часы."}'
            )
            self._add_error(
                errors=errors,
                field_error='start_datetime',
                text_error=text_error,
            )
            return

        # Проверка 2: Наложение на другие существующие записи мастера
        overlapping = appontment_model.objects.select_for_update().filter(
            master=self.master,
            start_datetime__lt=end,
            end_datetime__gt=self.start_datetime
        ).exclude(status='cancelled').order_by('start_datetime')

        if overlapping.exists():
            # Формируем список всех конфликтов
            conflict_lines = []
            for conflict in overlapping:
                conflict_start = timezone.localtime(conflict.start_datetime)
                conflict_end = timezone.localtime(conflict.end_datetime)
                conflict_lines.append(
                    f'({conflict_start:%H:%M} – {conflict_end:%H:%M})'
                )

            self._add_error(
                errors=errors,
                field_error='start_datetime',
                text_error='Следующее время занято: ' + ', '.join(conflict_lines),
            )
