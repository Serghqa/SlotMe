from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.admin import RelatedOnlyFieldListFilter
from django.db.models import Q
from .models import Master, WorkSchedule, ScheduleException
from django.urls import reverse
from django.utils.html import format_html


User = get_user_model()


class WorkScheduleInline(admin.TabularInline):
    model = WorkSchedule
    extra = 0
    fields = ('day_of_week', 'start_time', 'end_time', 'is_working')


class ScheduleExceptionInline(admin.TabularInline):
    model = ScheduleException
    extra = 0


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    fields = ('user', 'services', 'is_active')

    list_display = ('master_name', 'phone', 'is_active', 'services_list')
    list_filter = ('is_active', ('services', RelatedOnlyFieldListFilter))
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__phone')
    filter_horizontal = ('services',)
    inlines = [WorkScheduleInline, ScheduleExceptionInline]

    def get_queryset(self, request):
        """Оптимизация запросов к БД (решение проблемы N+1)."""
        queryset = super().get_queryset(request)
        # select_related подгружает данные пользователя одним JOIN-запросом
        # prefetch_related эффективно подтягивает многие-ко-многим (услуги)
        return queryset.select_related('user').prefetch_related('services')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Показывает в выпадающем списке только пользователей без привязки к мастеру."""
        if db_field.name == "user":
            # 1. Базовый запрос: ищем пользователей с ролью 'master' или 'client'
            # (исключаем суперадминов/персонал, если это необходимо)
            queryset = User.objects.filter(is_superuser=False)
            # Получаем ID мастера, которого сейчас редактируют (если это редактирование)
            object_id = request.resolver_match.kwargs.get('object_id')

            if object_id:
                # Если редактируем: исключаем ВСЕХ мастеров, КРОМЕ текущего
                queryset = queryset.filter(
                    Q(master_profile__isnull=True) | Q(master_profile__id=object_id)
                )
            else:
                # Если создаем нового: показываем только пользователей БЕЗ профиля мастера
                queryset = queryset.filter(master_profile__isnull=True)
            # Оптимизируем загрузку (опционально)
            kwargs["queryset"] = queryset.distinct()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ('master', 'day_of_week', 'start_time', 'end_time', 'is_working')
    list_filter = ('master', 'day_of_week', 'is_working')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Показывает в выпадающем списке только АКТИВНЫХ мастеров."""
        if db_field.name == "master":
            kwargs["queryset"] = Master.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ScheduleException)
class ScheduleExceptionAdmin(admin.ModelAdmin):
    fields = ('master', 'date', 'is_working', 'start_time', 'end_time', 'reason')
    list_display = ('master', 'date', 'start_time', 'end_time', 'reason', 'is_working')
    list_filter = ('master', 'is_working', 'date')
    search_fields = ('reason',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Показывает в выпадающем списке только АКТИВНЫХ мастеров."""
        if db_field.name == "master":
            kwargs["queryset"] = Master.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
