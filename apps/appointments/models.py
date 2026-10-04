from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.choices import StatusChoices
from .utils import AppointmentValidationMixin


class Appointment(AppointmentValidationMixin, models.Model):
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
    end_datetime = models.DateTimeField(blank=True, verbose_name='Конец')
    status = models.CharField(
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.BOOKED,
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
                condition=~models.Q(status=StatusChoices.CANCELLED),
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
        local_start = timezone.localtime(self.start_datetime)
        local_end = timezone.localtime(self.end_datetime)
        return f"Запись: ({local_start:%d.%m.%Y %H:%M}-{local_end:%H:%M})"

    def clean(self):
        self.set_end_datetime()
        self.clean_appointment()

    def save(self, *args, **kwargs):
        self.set_end_datetime()
        if self.status == StatusChoices.CANCELLED and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def set_end_datetime(self):
        """Автоматически устанавливает end_datetime на основе start_datetime и длительности услуги."""
        if self.service_id and self.start_datetime:
            self.end_datetime = self.start_datetime + self.service.duration

    @property
    def is_booked(self):
        return self.status == StatusChoices.BOOKED

    @property
    def is_completed(self):
        return self.status == StatusChoices.COMPLETED

    @property
    def is_cancelled(self):
        return self.status == StatusChoices.CANCELLED

    @property
    def is_no_show(self):
        return self.status == StatusChoices.NO_SHOW

    @property
    def is_past(self):
        """Проверяет, что запись уже началась/прошла."""
        return self.start_datetime < timezone.now()

    @property
    def can_be_cancelled(self):
        """Проверяет, что запись можно отменить."""
        return self.is_booked and not self.is_past

    @property
    def can_be_closed(self):
        """Проверяет, что запись можно закрыть (завершить или отметить как неявку)."""
        return StatusChoices.CANCELLED not in self.allowed_status_transitions

    @property
    def allowed_status_transitions(self):
        """Возвращает список допустимых статусов для перехода."""

        if self.status == StatusChoices.CANCELLED:
            return [StatusChoices.CANCELLED]
        if self.status in [StatusChoices.COMPLETED, StatusChoices.NO_SHOW]:
            return [StatusChoices.COMPLETED, StatusChoices.NO_SHOW]
        if self.status == StatusChoices.BOOKED:
            if self.is_past:
                return [StatusChoices.BOOKED, StatusChoices.COMPLETED, StatusChoices.NO_SHOW]
            else:
                return [StatusChoices.BOOKED, StatusChoices.CANCELLED]

        return [self.status]
