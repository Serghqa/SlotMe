from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_display', 'is_active')
    list_filter = ('is_active', ('masters', RelatedOnlyFieldListFilter))
    list_per_page = 15
    search_fields = ('name', 'description')
    list_editable = ('is_active',)

    @admin.display(description='Длительность')
    def duration_display(self, obj):
        return obj.duration_display
