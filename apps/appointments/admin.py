from django.contrib import admin
from django.core.exceptions import ValidationError
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
