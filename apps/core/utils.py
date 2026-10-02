from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.urls import reverse


def get_paginated_page(queryset, page_number, per_page=10):
    """
    Универсальная пагинация QuerySet.
    """
    paginator = Paginator(queryset, per_page)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return page_obj


def get_next_url(request, default_url):
    """
    Получение URL для редиректа после выполнения действия.
    Если в GET-параметрах есть 'next', проверяем его на допустимость и возвращаем.
    В противном случае возвращаем default_url.
    """
    next_url = request.GET.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return next_url
    return default_url


def get_url_with_params(viewname, url_kwargs=None, **kwargs):
    """
    Возвращает URL с дополнительными параметрами.
    """
    base_url = reverse(viewname, kwargs=url_kwargs)
    clean_kwargs = {k: v for k, v in kwargs.items() if v is not None and v != ''}
    if clean_kwargs:
        base_url = f"{base_url}?{urlencode(clean_kwargs)}"
    return base_url
