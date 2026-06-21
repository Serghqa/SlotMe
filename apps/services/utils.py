from datetime import timedelta


class ServiceValidationMixin:
    """Миксин для валидации Service."""

    def clean(self):
        cleaned_data = super().clean()
        duration = cleaned_data.get('duration')

        if duration is not None and duration <= timedelta(0):
            self.add_error(
                'duration',
                'Длительность должна быть больше нуля.'
            )

        return cleaned_data
