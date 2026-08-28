from django.contrib import admin
from django.utils import timezone
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('client', 'master', 'service', 'start_datetime', 'end_datetime', 'status', 'created_at')
    list_filter = ('status', 'master')
    search_fields = ('client__username', 'client__first_name', 'client__last_name', 'master__user__username')
    readonly_fields = ('end_datetime', 'created_at', 'cancelled_at')
    date_hierarchy = 'start_datetime'
    raw_id_fields = ('client', 'master', 'service')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('client', 'master__user', 'service')

    def get_readonly_fields(self, request, obj=None):
        base_readonly = ('end_datetime', 'created_at', 'cancelled_at')
        if not obj:
            return base_readonly

        now = timezone.now()

        # 1. Забронирована и в БУДУЩЕМ -> закрываем всё, кроме статуса и причины
        if obj.status == 'booked' and now < obj.start_datetime:
            return ('client', 'master', 'service', 'start_datetime', 'end_datetime', 'created_at', 'cancelled_at')
        # 2. Забронирована и в ПРОШЛОМ -> закрываем всё, кроме статуса
        if obj.status == 'booked' and now >= obj.start_datetime:
            return ('client', 'master', 'service', 'start_datetime', 'end_datetime', 'created_at', 'cancelled_at', 'cancel_reason')
        # 3. ОТМЕНЕНА -> закрываем всё, кроме причины отмены (статус тоже закрыт!)
        elif obj.status == 'cancelled':
            return ('client', 'master', 'service', 'start_datetime', 'end_datetime', 'created_at', 'status', 'cancelled_at')
        # 4. ЗАВЕРШЕНА или НЕЯВКА -> закрываем абсолютно всё
        else:
            return ('client', 'master', 'service', 'start_datetime', 'end_datetime', 'created_at', 'status', 'cancelled_at', 'cancel_reason')

    def get_fields(self, request, obj=None):
        if not obj:
            return ['client', 'master', 'service', 'start_datetime', 'status']

        now = timezone.now()
        # 1. Забронирована и в БУДУЩЕМ -> редактируем статус (отмена) + причина
        if obj.status == 'booked' and now < obj.start_datetime:
            return ['client', 'master', 'service', 'start_datetime', 'end_datetime', 'created_at', 'status', 'cancel_reason']
        # 2. Забронирована и в ПРОШЛОМ -> редактируем статус (завершить/неявка)
        elif obj.status == 'booked' and now >= obj.start_datetime:
            return ['client', 'master', 'service', 'start_datetime', 'end_datetime', 'created_at', 'status']
        # 3. ОТМЕНЕНА -> только корректировка причины
        elif obj.status == 'cancelled':
            return ['client', 'master', 'service', 'start_datetime', 'end_datetime', 'created_at', 'status', 'cancel_reason', 'cancelled_at']
        # 4. ЗАВЕРШЕНА или НЕЯВКА -> только просмотр
        else:
            return ['client', 'master', 'service', 'start_datetime', 'end_datetime', 'created_at', 'status']

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        if obj and 'status' in form.base_fields:
            now = timezone.now()
            # Если в будущем: можно оставить booked или перевести в cancelled
            if obj.status == 'booked' and now < obj.start_datetime:
                form.base_fields['status'].choices = [
                    ('booked', 'Забронирована'),
                    ('cancelled', 'Отменена'),
                ]
            # Если в прошлом: можно только completed или no_show
            elif obj.status == 'booked' and now >= obj.start_datetime:
                form.base_fields['status'].choices = [
                    ('completed', 'Завершена'),
                    ('no_show', 'Неявка'),
                ]

        return form