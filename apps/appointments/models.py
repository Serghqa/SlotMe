from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Забронирована'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
        ('no_show', 'Неявка'),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name='Клиент'
    )
    master = models.ForeignKey(
        'masters.Master',
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name='Мастер'
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name='Услуга'
    )
    start_datetime = models.DateTimeField(verbose_name='Начало')
    end_datetime = models.DateTimeField(verbose_name='Конец', editable=False)
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='booked',
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата отмены')
    cancel_reason = models.TextField(blank=True, verbose_name='Причина отмены')

    class Meta:
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'
        ordering = ['-start_datetime']
        constraints = [
            models.UniqueConstraint(
                fields=['master', 'start_datetime'],
                condition=~models.Q(status='cancelled'),
                name='unique_active_booking',
                violation_error_message='Мастер уже занят в это время'
            )
        ]
        indexes = [
            models.Index(fields=['master', 'start_datetime']),
            models.Index(fields=['client', 'start_datetime']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Запись: ({self.start_datetime:%d.%m.%Y %H:%M}-{self.end_datetime:%H:%M})"

    def save(self, *args, **kwargs):
        if self.service:
            self.end_datetime = self.start_datetime + self.service.duration
        super().save(*args, **kwargs)

    @property
    def is_past(self):
        return self.start_datetime < timezone.now()

    @property
    def can_be_cancelled(self):
        return self.status == 'booked' and not self.is_past
