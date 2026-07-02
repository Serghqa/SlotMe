from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect


def master_required(view_func):
    """Пускает только активных мастеров."""
    def check(user):
        return user.is_authenticated and user.is_master
    return user_passes_test(check, login_url='users:login')(view_func)


def admin_required(view_func):
    """Пускает только администраторов."""
    def check(user):
        return user.is_authenticated and user.is_admin
    return user_passes_test(check, login_url='users:login')(view_func)
