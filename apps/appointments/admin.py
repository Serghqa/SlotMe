from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter
from apps.core.choices import StatusChoices
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('client', 'master', 'service', 'start_datetime', 'end_datetime', 'status', 'created_at')
    list_filter = ('status', ('master', RelatedOnlyFieldListFilter))
    search_fields = ('client__email', 'client__first_name', 'client__phone', 'master__user__email', 'master__user__first_name')
    date_hierarchy = 'start_datetime'
    raw_id_fields = ('client', 'master', 'service')

    BASE_READONLY_FIELDS = {'end_datetime', 'created_at', 'cancelled_at'}
    ALL_FIELDS = ['client', 'master', 'service', 'start_datetime', 'end_datetime', 'created_at', 'status', 'cancel_reason', 'cancelled_at']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('client', 'master__user', 'service')

    def get_readonly_fields(self, request, obj=None):
        # При создании записи базовые поля недоступны для редактирования
        if not obj:
            return tuple(self.BASE_READONLY_FIELDS)

        readonly_fields = set(self.ALL_FIELDS)
        readonly_fields.discard('status')

        if StatusChoices.CANCELLED in obj.allowed_status_transitions:
            readonly_fields.discard('cancel_reason')  # Причина отмены доступна только для записей, которые можно отменить

        return tuple(readonly_fields)

    def get_fields(self, request, obj=None):
        # При создании записи запрашиваем только необходимый минимум
        if not obj:
            return ['client', 'master', 'service', 'start_datetime', 'status']

        fields = self.ALL_FIELDS.copy()

        if StatusChoices.CANCELLED not in obj.allowed_status_transitions:
            fields.remove('cancel_reason')  # Причина отмены неактуальна для записей, которые нельзя отменить

        if obj.status != StatusChoices.CANCELLED:
            fields.remove('cancelled_at')  # Дата отмены неактуальна для записей, которые не отменены

        return fields

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)

        if 'status' not in form.base_fields:
            return form

        # Если создаем новую запись, доступен только один статус
        if not obj:
            form.base_fields['status'].choices = [(StatusChoices.BOOKED, StatusChoices.BOOKED.label)]
            return form

        # Для существующей записи берем доступные переходы из модели (метод allowed_status_transitions)
        status_labels = dict(StatusChoices.choices)
        form.base_fields['status'].choices = [
            (choice, status_labels[choice]) for choice in obj.allowed_status_transitions
        ]

        return form
