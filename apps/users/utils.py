class BootstrapFormMixin:
    """
    Миксин для добавления классов Bootstrap к полям формы и отображения ошибок.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def add_error(self, field, error):
        super().add_error(field, error)
        if field and field in self.fields:
            widget = self.fields[field].widget
            css = widget.attrs.get('class', '')
            if 'is-invalid' not in css:
                widget.attrs['class'] = f'{css} is-invalid'.strip()
