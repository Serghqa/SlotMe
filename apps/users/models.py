from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class CustomUserManager(BaseUserManager):
    def create_user(self, email, first_name, phone, password=None, **extra_fields):
        if not email:
            raise ValueError('Email является обязательным полем')
        if not first_name:
            raise ValueError('Имя является обязательным полем')
        if not phone:
            raise ValueError('Телефон является обязательным полем')

        email = self.normalize_email(email).lower()

        user = self.model(
            email=email,
            first_name=first_name,
            phone=phone,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self.db)

        return user

    def create_superuser(self, email, first_name, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, first_name, phone, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name='Электронная почта')
    phone = PhoneNumberField(region='RU', verbose_name='Телефон')
    first_name = models.CharField(max_length=30, verbose_name='Имя')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'phone']

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.get_full_name() or self.first_name}"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    @property
    def is_master(self):
        return hasattr(self, 'master_profile') and self.master_profile.is_active

    @property
    def is_admin(self):
        return self.is_staff or self.is_superuser
