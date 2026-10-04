from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    """
    Возвращает строку GET-параметров, обновляя или добавляя новые значения.
    """
    query_params = context['request'].GET.copy()

    for key, value in kwargs.items():
        if value is not None and value != '':
            query_params[key] = value
        else:
            query_params.pop(key, None)

    return query_params.urlencode()


@register.inclusion_tag('includes/pagination.html', takes_context=True)
def render_pagination(context, page_obj):
    """
    Рендерит универсальный блок пагинации.
    Передает текущий контекст запроса (для param_replace) и сам объект страницы.
    """

    request = context['request']
    return {
        'request': request,
        'page_obj': page_obj,
    }
