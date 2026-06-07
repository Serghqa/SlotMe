from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'phone',)
    list_filter = ('role',)
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone',)
    list_editable = ('role',)
    fieldsets = list(BaseUserAdmin.fieldsets) + [
        ('Дополнительно', {'fields': ('role', 'phone')}),
    ]
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительно', {'fields': ('role', 'email', 'phone')}),
    )
