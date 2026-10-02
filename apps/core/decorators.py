from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def master_required(view_func):
    """
    Декоратор для проверки, что пользователь является мастером.
    """
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_active_master:
            raise PermissionDenied('Доступ только для мастеров')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """
    Декоратор для проверки, что пользователь является администратором.
    """
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied('Доступ только для администраторов')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def client_required(view_func):
    """
    Декоратор для проверки, что пользователь является клиентом.
    """
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_client:
            raise PermissionDenied('Доступ только для клиентов')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
