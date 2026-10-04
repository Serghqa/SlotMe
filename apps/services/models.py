from django.db import models
from django.core.validators import MinValueValidator
from datetime import timedelta
from .utils import ServiceValidationMixin


class Service(ServiceValidationMixin, models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Стоимость'
    )
    duration = models.DurationField(
        verbose_name='Длительность',
        help_text='Пример: 1:30:00 — полтора часа'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(duration__gt=timedelta(0)),
                name='duration_positive',
                violation_error_message='Длительность должна быть положительной',
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name='price_non_negative',
                violation_error_message='Стоимость не может быть отрицательной',
            ),
        ]

    @property
    def duration_display(self):
        total = int(self.duration.total_seconds())
        h, m = divmod(total // 60, 60)
        if h and m:
            return f'{h} ч {m} мин'
        if h:
            return f'{h} ч'
        return f'{m} мин'

    def __str__(self):
        return f"{self.name} — {self.price:.0f} ₽ ({self.duration_display})"

    def clean(self):
        super().clean()
        self.clean_service()
