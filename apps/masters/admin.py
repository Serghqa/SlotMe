from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.admin import RelatedOnlyFieldListFilter
from .models import Master, WorkSchedule, ScheduleException
from .utils import FilterActiveMasterMixin, ScheduleInlineMixin, ReadonlyFieldOnEditMixin


User = get_user_model()


class WorkScheduleInline(ScheduleInlineMixin, admin.TabularInline):
    model = WorkSchedule
    extra = 0
    fields = ('day_of_week', 'start_time', 'end_time', 'is_working')


class ScheduleExceptionInline(ScheduleInlineMixin, admin.TabularInline):
    model = ScheduleException
    extra = 0


@admin.register(Master)
class MasterAdmin(ReadonlyFieldOnEditMixin, admin.ModelAdmin):
    fields = ('user', 'is_active', 'services', 'bio', 'photo')
    list_per_page = 15
    list_display = ('master_name', 'master_email', 'master_phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__email', 'user__first_name', 'user__phone')
    filter_horizontal = ('services',)
    inlines = [WorkScheduleInline, ScheduleExceptionInline]
    readonly_field_name = 'user'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Показывает в выпадающем списке только пользователей без привязки к мастеру."""
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(
                master_profile__isnull=True,
                appointments__isnull=True,
                is_superuser=False,
                is_staff=False,
                is_active=True
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description='Мастер', ordering='user__first_name')
    def master_name(self, obj):
        return obj.user.display_name

    @admin.display(description='Электронная почта', ordering='user__email')
    def master_email(self, obj):
        return obj.user.email

    @admin.display(description='Телефон', ordering='user__phone')
    def master_phone(self, obj):
        return obj.user.phone


@admin.register(WorkSchedule)
class WorkScheduleAdmin(ReadonlyFieldOnEditMixin, FilterActiveMasterMixin, admin.ModelAdmin):
    fields = ('master', 'day_of_week', 'start_time', 'end_time', 'is_working')
    list_display = ('master', 'day_of_week', 'start_time', 'end_time', 'is_working')
    list_filter = ('master__is_active', 'day_of_week', 'is_working', ('master', RelatedOnlyFieldListFilter))
    list_per_page = 15
    list_select_related = ('master__user',)
    search_fields = ('master__user__first_name', 'master__user__phone', 'master__user__email')
    readonly_field_name = 'master'



@admin.register(ScheduleException)
class ScheduleExceptionAdmin(ReadonlyFieldOnEditMixin, FilterActiveMasterMixin, admin.ModelAdmin):
    fields = ('master', 'date', 'is_working', 'start_time', 'end_time', 'reason')
    list_display = ('master', 'date', 'is_working', 'start_time', 'end_time', 'reason')
    list_filter = ('master__is_active', 'is_working', 'date', ('master', RelatedOnlyFieldListFilter))
    list_per_page = 15
    list_select_related = ('master__user',)
    search_fields = ('reason', 'master__user__first_name', 'master__user__phone', 'master__user__email')
    readonly_field_name = 'master'
