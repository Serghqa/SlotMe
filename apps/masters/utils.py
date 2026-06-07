from django.apps import apps
from django.core.exceptions import ValidationError


class FilterActiveMasterMixin:
    """
    Миксин для администраторских классов, который фильтрует
    queryset ForeignKey 'master' на активных мастеров.
    Предполагается, что модель имеет поле 'master', связанное с Master.
    """
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Показывает в выпадающем списке только АКТИВНЫХ мастеров."""
        if db_field.name == "master":
            Master = apps.get_model('masters', 'Master')

            kwargs["queryset"] = Master.objects.filter(is_active=True).select_related('user')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class WorkingHoursMixin:
    """Миксин для моделей с рабочими часами"""

    def clean_working_hours(self):
        """Валидация и очистка рабочих часов"""
        if self.is_working:
            errors = {}
            if not self.start_time:
                errors['start_time'] = 'Укажите время начала работы для рабочего дня.'
            if not self.end_time:
                errors['end_time'] = 'Укажите время окончания работы для рабочего дня.'
            if self.start_time and self.end_time and self.start_time >= self.end_time:
                errors['end_time'] = 'Время окончания работы должно быть позже времени начала.'
            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Гарантированное зануление часов для выходных дней при любом сохранении в БД."""
        if not self.is_working:
            self.start_time = None
            self.end_time = None
        super().save(*args, **kwargs)


class ScheduleInlineMixin:
    """Миксин для оптимизации запросов в админке при работе с расписанием мастера"""

    def get_queryset(self, request):
        """Предзагрузка связанных данных мастера для строк инлайна."""
        return super().get_queryset(request).select_related('master__user')
