from django.core.exceptions import ValidationError
from datetime import timedelta


class ServiceValidationMixin:
    """Миксин для валидации Service."""

    def clean_service(self):
        if self.duration is not None:
            if self.duration <= timedelta(0):
                raise ValidationError({'duration': 'Длительность должна быть больше нуля.'})
