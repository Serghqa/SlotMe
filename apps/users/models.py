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
        super().save(*args, **kwargs)

        from apps.masters.models import Master
        # Автосоздание Master при роли 'master'
        if self.role == 'master':
            master, created = Master.objects.get_or_create(user=self)
            if not created and not master.is_active:
                master.is_active = True
                master.save(update_fields=['is_active'])
        else:
            Master.objects.filter(user=self).update(is_active=False)
