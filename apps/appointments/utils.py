from django.apps import apps
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.choices import StatusChoices, WeekdaysChoices


class AppointmentValidationMixin:
    """Миксин для комплексной валидации Appointment в Django-Admin"""

    def clean_appointment(self):
        """
        Точка входа валидации. Запускает нужный набор проверок в зависимости
        от того, создаётся запись или обновляется.
        """
        AppointmentModel = apps.get_model('appointments', 'Appointment')

        errors = {}

        if not all([self.master_id, self.service_id, self.client_id, self.start_datetime]):
            raise ValidationError('Заполните обязательные поля.')

        if not self.pk:
            self._validate_user(errors)
            self._validate_master(errors)
            self._validate_service(errors)
            self._validate_master_service(errors)
            self._validate_status_create(errors)
            self._validate_not_past_time(errors)
            if 'start_datetime' not in errors:
                self._validate_master_time_availability(errors, AppointmentModel)
        else:
            self._validate_status_update(errors, AppointmentModel)

        if errors:
            raise ValidationError(errors)

    def _add_error(self, errors: dict, field_error: str, text_error: str):
        """
        Добавляет сообщение об ошибке к указанному полю, накапливая их в словаре.
        """
        errors.setdefault(field_error, []).append(text_error)

    def _validate_user(self, errors):
        """
        Проверяет, что клиент может быть записан на приём.
        """
        is_admin = self.client.is_staff
        is_master = self.client.is_master
        user_name = self.client.display_name
        if is_admin or is_master:
            self._add_error(
                errors=errors,
                field_error='client',
                text_error=f"Пользователь {user_name} является сотрудником и не может быть записан."
            )
        if not self.client.is_active:
            self._add_error(
                errors=errors,
                field_error='client',
                text_error=f"Пользователь {user_name} не активный."
            )

    def _validate_service(self, errors):
        """
        Проверяет, что услуга активна.
        """
        if not self.service.is_active:
            self._add_error(
                errors=errors,
                field_error='service',
                text_error=f"Услуга {self.service.name} неактивна."
            )

    def _validate_master(self, errors):
        """
        Проверяет, что мастер активен.
        """
        if not self.master.is_active:
            self._add_error(
                errors=errors,
                field_error='master',
                text_error=f"Мастер {self.master.user.display_name} неактивен.",
            )

    def _validate_master_service(self, errors):
        """
        Проверяет, что выбранный мастер действительно предоставляет
        выбранную услугу.
        """
        if not self.master.services.filter(id=self.service_id).exists():
            self._add_error(
                errors=errors,
                field_error='service',
                text_error=f"Мастер {self.master.user.display_name} не предоставляет услугу {self.service.name}.",
            )

    def _validate_status_create(self, errors):
        """
        Проверяет, что новая запись создаётся только в статусе booked.
        """
        if self.status != StatusChoices.BOOKED:
            self._add_error(
                errors=errors,
                field_error='status',
                text_error=f"Новая запись может быть только в статусе {StatusChoices.BOOKED.label}.",
            )

    def _validate_not_past_time(self, errors):
        """
        Проверяет, что время начала записи не находится в прошлом.
        """
        if self.is_past:
            self._add_error(
                errors=errors,
                field_error='start_datetime',
                text_error='Нельзя создать запись на прошедшее время.',
            )

    def _validate_status_update(self, errors, appontment_model):
        """
        Проверяет допустимость смены статуса существующей записи.
        """
        # Для существующей записи проверяем переходы
        # Сначала получаем старый статус из базы данных, чтобы сравнить его с новым статусом.
        old_status = appontment_model.objects.only('status').get(pk=self.pk).status

        # 'cancelled' можно установить только для будущих записей
        if self.is_cancelled and self.is_past:
            self._add_error(
                errors=errors,
                field_error='status',
                text_error='Отменить запись можно только до её начала.',
            )
            return

        # Проверяем, что поле "Причина отмены" заполнено только для отменённых записей
        if not self.is_cancelled and self.cancel_reason:
            self._add_error(
                errors=errors,
                field_error='cancel_reason',
                text_error='Причина отмены может быть указана только для отменённых записей.',
            )
            return

        # Нельзя менять статус отменённой записи
        if old_status == StatusChoices.CANCELLED and not self.is_cancelled:
            self._add_error(
                errors=errors,
                field_error='status',
                text_error='Нельзя менять статус отмененной записи.',
            )
            return

        # Статус completed можно изменить толко на no_show и наоборот
        if old_status in [StatusChoices.COMPLETED, StatusChoices.NO_SHOW] and \
            self.status not in [StatusChoices.COMPLETED, StatusChoices.NO_SHOW]:
            text_error = (
                f"Завершённая запись может быть только {StatusChoices.COMPLETED.label} или {StatusChoices.NO_SHOW.label}"
            )
            self._add_error(
                errors=errors,
                field_error='status',
                text_error=text_error,
            )
            return

        # Запрещаем 'completed', 'no_show' для будущих записей
        if self.status in [StatusChoices.COMPLETED, StatusChoices.NO_SHOW] and not self.is_past:
            text_error = (
                f"Статус {self.status.label} можно установить только для прошедших записей."
            )
            self._add_error(
                errors=errors,
                field_error='status',
                text_error=text_error,
            )
            return

    def _validate_master_time_availability(self, errors, appontment_model):
        """
        Проверяет, что запись укладывается в рабочее время мастера
        и не пересекается с другими активными записями.
        """
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
                    text_error=f"{booking_date:%d.%m.%Y} - мастер не работает. Причина: {reason}",
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
                    text_error=f"{booking_date:%d.%m.%Y} ({WeekdaysChoices(day_of_week).label}) — нерабочий день.",
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
                f"Запись выходит за рамки рабочего времени мастера в этот день ({work_start:%H:%M} – {work_end:%H:%M})."
                f" {reason if reason else 'Нерабочие часы.'}"
            )
            self._add_error(
                errors=errors,
                field_error='start_datetime',
                text_error=text_error,
            )
            return

        # Проверка 2: Наложение на другие существующие записи мастера
        overlapping = appontment_model.objects.filter(
            master=self.master,
            start_datetime__lt=end,
            end_datetime__gt=self.start_datetime
        ).exclude(status=StatusChoices.CANCELLED).order_by('start_datetime')

        if overlapping.exists():
            # Формируем список всех конфликтов
            conflict_lines = []
            for conflict in overlapping:
                conflict_start = timezone.localtime(conflict.start_datetime)
                conflict_end = timezone.localtime(conflict.end_datetime)
                conflict_lines.append(
                    f"({conflict_start:%H:%M} – {conflict_end:%H:%M})"
                )

            self._add_error(
                errors=errors,
                field_error='start_datetime',
                text_error='Следующее время занято: ' + ', '.join(conflict_lines),
            )
