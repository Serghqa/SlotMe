from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.choices import WeekdaysChoices
from .utils import WorkingHoursMixin


class MasterManager(models.Manager):
    """Менеджер, который всегда подгружает пользователя"""

    def get_queryset(self):
        return super().get_queryset().select_related('user')


class Master(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='master_profile',
        verbose_name='Пользователь'
    )
    services = models.ManyToManyField(
        'services.Service',
        blank=True,
        related_name='masters',
        verbose_name='Услуги'
    )
    bio = models.TextField(blank=True, verbose_name='О себе')
    photo = models.ImageField(
        upload_to='masters/',
        blank=True,
        verbose_name='Фото'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    objects = MasterManager()

    class Meta:
        verbose_name = 'Мастер'
        verbose_name_plural = 'Мастера'

    def __str__(self):
        return self.user.first_name or self.user.email


class WorkSchedule(WorkingHoursMixin, models.Model):
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='schedule',
        verbose_name='Мастер'
    )
    start_time = models.TimeField(verbose_name='Начало работы', blank=True, null=True)
    end_time = models.TimeField(verbose_name='Конец работы', blank=True, null=True)
    day_of_week = models.PositiveSmallIntegerField(
        choices=WeekdaysChoices.choices,
        verbose_name='День недели'
    )
    is_working = models.BooleanField(default=True, verbose_name='Рабочий день')

    class Meta:
        verbose_name = 'Рабочее расписание'
        verbose_name_plural = 'Рабочие расписания'
        ordering = ['master', 'day_of_week']
        constraints = [
            models.UniqueConstraint(
                fields=['master', 'day_of_week'],
                name='unique_master_day_of_week'
            )
        ]

    def clean(self):
        super().clean()
        self.clean_working_hours()

    def __str__(self):
        if not self.is_working:
            return f"{self.master.user.display_name} — {self.get_day_of_week_display()}: выходной"
        return f"{self.master.user.display_name} — {self.get_day_of_week_display()}: {self.start_time:%H:%M}–{self.end_time:%H:%M}"


class ScheduleException(WorkingHoursMixin, models.Model):
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='exceptions',
        verbose_name='Мастер'
    )
    date = models.DateField(verbose_name='Дата')
    start_time = models.TimeField(verbose_name='Начало работы', blank=True, null=True)
    end_time = models.TimeField(verbose_name='Конец работы', blank=True, null=True)
    is_working = models.BooleanField(
        default=False,
        verbose_name='Рабочий день',
        help_text='Если выключено — выходной. Если включено — особые часы.'
    )
    reason = models.CharField(max_length=100, blank=True, verbose_name='Причина')

    class Meta:
        verbose_name = 'Исключение в расписании'
        verbose_name_plural = 'Исключения в расписании'
        ordering = ['master', '-date']
        constraints = [
            models.UniqueConstraint(
                fields=['master', 'date'],
                name='unique_master_date'
            )
        ]

    def clean(self):
        super().clean()
        self.clean_working_hours()

    def __str__(self):
        if self.is_working:
            return f"{self.master.user.display_name} — {self.date:%d.%m.%Y}: {self.start_time:%H:%M}–{self.end_time:%H:%M}"
        return f"{self.master.user.display_name} — {self.date:%d.%m.%Y}: выходной"
