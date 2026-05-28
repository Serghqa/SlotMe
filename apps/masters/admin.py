from django.contrib import admin
from .models import Master, WorkSchedule, ScheduleException


class WorkScheduleInline(admin.TabularInline):
    model = WorkSchedule
    extra = 7  # сразу 7 строк под все дни недели


class ScheduleExceptionInline(admin.TabularInline):
    model = ScheduleException
    extra = 1


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_active')
    list_filter = ('is_active', 'services')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    filter_horizontal = ('services',)
    inlines = [WorkScheduleInline, ScheduleExceptionInline]


@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ('master', 'day_of_week', 'start_time', 'end_time', 'is_working')
    list_filter = ('master', 'day_of_week', 'is_working')


@admin.register(ScheduleException)
class ScheduleExceptionAdmin(admin.ModelAdmin):
    list_display = ('master', 'date', 'is_working', 'start_time', 'end_time', 'reason')
    list_filter = ('master', 'is_working')
