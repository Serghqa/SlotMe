from django.db import models
from django.core.validators import MinValueValidator
from datetime import timedelta


class Service(models.Model):
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
                violation_error_message='Длительность должна быть положительной'
            )
        ]

    def __str__(self):
        return f"{self.name} — {self.price}₽ ({self.duration})"
