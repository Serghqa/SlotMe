from .models import Master


class FilterActiveMasterMixin:
    """
    Миксин для администраторских классов, который фильтрует
    queryset ForeignKey 'master' на активных мастеров.
    Предполагается, что модель имеет поле 'master', связанное с Master.
    """
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Показывает в выпадающем списке только АКТИВНЫХ мастеров."""
        if db_field.name == "master":
            kwargs["queryset"] = Master.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
