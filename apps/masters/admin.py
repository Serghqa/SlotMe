from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.admin import RelatedOnlyFieldListFilter
from .models import Master, WorkSchedule, ScheduleException
from .utils import FilterActiveMasterMixin, ScheduleInlineMixin


User = get_user_model()


class WorkScheduleInline(ScheduleInlineMixin, admin.TabularInline):
    model = WorkSchedule
    extra = 0
    fields = ('day_of_week', 'start_time', 'end_time', 'is_working')


class ScheduleExceptionInline(ScheduleInlineMixin, admin.TabularInline):
    model = ScheduleException
    extra = 0


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    fields = ('user', 'services', 'is_active')
    list_per_page = 15
    list_display = ('master_name', 'phone', 'is_active', 'services_list')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__phone')
    filter_horizontal = ('services',)
    inlines = [WorkScheduleInline, ScheduleExceptionInline]

    def get_queryset(self, request):
        """Оптимизация запросов к БД (решение проблемы N+1)."""
        queryset = super().get_queryset(request)
        # prefetch_related эффективно подтягивает многие-ко-многим (услуги)
        return queryset.prefetch_related('services')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Показывает в выпадающем списке только пользователей без привязки к мастеру."""
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(master_profile__isnull=True)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        """Если объект редактируется, делаем поле 'user' доступным только для чтения."""
        if obj:
            return ('user',)
        return ()


    @admin.display(description='Мастер')
    def master_name(self, obj):
        return obj.user.username

    @admin.display(description='Телефон')
    def phone(self, obj):
        return obj.user.phone

    @admin.display(description='Услуги')
    def services_list(self, obj):
        services = obj.services.all()
        services_str = ', '.join(s.name for s in services[:3])
        if len(services_str) > 50:
            services_str = services_str[:47] + '...'

        return services_str or "-"


@admin.register(WorkSchedule)
class WorkScheduleAdmin(FilterActiveMasterMixin, admin.ModelAdmin):
    list_display = ('master', 'day_of_week', 'start_time', 'end_time', 'is_working')
    list_filter = ('master__is_active', 'day_of_week', 'is_working')
    list_select_related = ('master__user',)
    search_fields = ('master__user__username', 'master__user__first_name', 'master__user__last_name')


@admin.register(ScheduleException)
class ScheduleExceptionAdmin(FilterActiveMasterMixin, admin.ModelAdmin):
    list_display = ('master', 'date', 'is_working', 'start_time', 'end_time', 'reason')
    list_filter = ('master__is_active', 'is_working', 'date')
    list_select_related = ('master__user',)
    search_fields = ('reason', 'master__user__username', 'master__user__first_name', 'master__user__last_name')
