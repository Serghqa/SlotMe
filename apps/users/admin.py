from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone')
    list_per_page = 15
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone',)

    fieldsets = list(BaseUserAdmin.fieldsets) + [
        ('Дополнительно', {'fields': ('phone',)}),
    ]
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительно', {'fields': ('email', 'phone')}),
    )
