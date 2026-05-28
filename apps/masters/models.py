from django.db import models
from django.conf import settings


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

    class Meta:
        verbose_name = 'Мастер'
        verbose_name_plural = 'Мастера'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"Мастер: {self.user.get_full_name() or self.user.username}"


class WorkSchedule(models.Model):
    DAY_CHOICES = [
        (0, 'Понедельник'),
        (1, 'Вторник'),
        (2, 'Среда'),
        (3, 'Четверг'),
        (4, 'Пятница'),
        (5, 'Суббота'),
        (6, 'Воскресенье'),
    ]
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='schedule',
        verbose_name='Мастер'
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name='День недели')
    start_time = models.TimeField(verbose_name='Начало работы')
    end_time = models.TimeField(verbose_name='Конец работы')
    is_working = models.BooleanField(default=True, verbose_name='Рабочий день')

    class Meta:
        verbose_name = 'Рабочее расписание'
        verbose_name_plural = 'Рабочее расписание'
        unique_together = ('master', 'day_of_week')
        ordering = ['master', 'day_of_week']

    def __str__(self):
        return f"{self.master} — {self.get_day_of_week_display()}: {self.start_time}–{self.end_time}"


class ScheduleException(models.Model):
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='exceptions',
        verbose_name='Мастер'
    )
    date = models.DateField(verbose_name='Дата')
    is_working = models.BooleanField(
        default=False,
        verbose_name='Рабочий день',
        help_text='Если выключено — выходной. Если включено — особые часы.'
    )
    start_time = models.TimeField(null=True, blank=True, verbose_name='Начало работы')
    end_time = models.TimeField(null=True, blank=True, verbose_name='Конец работы')
    reason = models.CharField(max_length=200, blank=True, verbose_name='Причина')

    class Meta:
        verbose_name = 'Исключение в расписании'
        verbose_name_plural = 'Исключения в расписании'
        unique_together = ('master', 'date')
        ordering = ['master', 'date']

    def __str__(self):
        if self.is_working:
            return f"{self.master} — {self.date}: {self.start_time}–{self.end_time}"
        return f"{self.master} — {self.date}: выходной"
