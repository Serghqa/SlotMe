from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('master', 'Мастер'),
        ('client', 'Клиент'),
    ]
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='client',
        verbose_name='Роль'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        # Проверяем, новый ли это пользователь
        is_new = self.pk is None
        old_role = None

        if not is_new:
            # Получаем старую роль из базы данных для сравнения
            old_role = User.objects.filter(pk=self.pk).values_list('role', flat=True).first()

        # Стандартное сохранение пользователя
        super().save(*args, **kwargs)

        from apps.masters.models import Master  # Импортируем здесь, чтобы избежать циклической зависимости

        # Логика 1: Новый пользователь с ролью master
        if is_new and self.role == 'master':
            Master.objects.get_or_create(user=self, defaults={'is_active': True})

        # Логика 2: Изменение роли у существующего пользователя
        elif not is_new and old_role != self.role:
            if self.role == 'master':
                # Меняем на master: активируем или создаем профиль
                master_profile, created = Master.objects.get_or_create(user=self, defaults={'is_active': True})
                if not created and not master_profile.is_active:
                    master_profile.is_active = True
                    # Используем update_fields, чтобы не триггерить save() Мастера и избежать рекурсии
                    master_profile.save(update_fields=['is_active'])

            elif old_role == 'master' and self.role != 'master':
                # Ушли с роли master: деактивируем профиль, если он есть
                master_profile = Master.objects.filter(user=self).first()
                if master_profile and master_profile.is_active:
                    master_profile.is_active = False
                    master_profile.save(update_fields=['is_active'])
