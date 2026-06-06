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
            from .models import Master

            kwargs["queryset"] = Master.objects.filter(is_active=True)
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
            if errors:
                raise ValidationError(errors)
        else:
            # Если выходной, зануляем время для чистоты данных
            self.start_time = None
            self.end_time = None
