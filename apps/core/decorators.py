from django.contrib.auth.decorators import user_passes_test


def check_is_master(user):
    """Проверяет, что пользователь авторизован и является активным мастером."""
    return user.is_authenticated and user.is_master


def check_is_admin(user):
    """Проверяет, что пользователь авторизован и является администратором."""
    return user.is_authenticated and user.is_admin


master_required = user_passes_test(check_is_master, login_url='users:login')
admin_required = user_passes_test(check_is_admin, login_url='users:login')
