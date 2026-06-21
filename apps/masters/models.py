from django.db import models, transaction
from django.conf import settings
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
        return self.user.get_full_name() or self.user.username or f'Мастер #{self.pk}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        with transaction.atomic():
            # Сначала сохраняем самого Мастера, чтобы получить pk (если он новый)
            super().save(*args, **kwargs)

            # Логика для создания и обновления
            if self.is_active:
                # Если активен — у пользователя железно должна быть роль 'master'
                if self.user.role != 'master':
                    self.user.role = 'master'
                    self.user.save(update_fields=['role'])
            else:
                # Если деактивирован (и это не создание нового с is_active=False)
                if not is_new and self.user.role == 'master':
                    self.user.role = 'client'
                    self.user.save(update_fields=['role'])


class WorkSchedule(WorkingHoursMixin, models.Model):
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
    start_time = models.TimeField(verbose_name='Начало работы', blank=True, null=True)
    end_time = models.TimeField(verbose_name='Конец работы', blank=True, null=True)
    day_of_week = models.IntegerField(choices=DAY_CHOICES, verbose_name='День недели')
    is_working = models.BooleanField(default=True, verbose_name='Рабочий день')

    class Meta:
        verbose_name = 'Рабочее расписание'
        verbose_name_plural = 'Рабочее расписание'
        unique_together = ('master', 'day_of_week')

    def clean(self):
        super().clean()
        self.clean_working_hours()

    def __str__(self):
        return f"{self.master} — {self.get_day_of_week_display()}: {self.start_time}–{self.end_time}"


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
        unique_together = ('master', 'date')

    def clean(self):
        super().clean()
        self.clean_working_hours()

    def __str__(self):
        if self.is_working:
            return f"{self.master} — {self.date}: {self.start_time}–{self.end_time}"
        return f"{self.master} — {self.date}: выходной"
