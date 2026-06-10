from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration', 'is_active')
    list_filter = ('is_active',)
    list_per_page = 15
    search_fields = ('name', 'description')
    list_editable = ('is_active',)
