from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def master_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not getattr(request.user, 'is_master', False):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not getattr(request.user, 'is_admin', False):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view
