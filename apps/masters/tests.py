from datetime import time, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Master, WorkSchedule, ScheduleException

User = get_user_model()
Service = apps.get_model('services', 'Service')

class MasterBusinessLogicTestCase(TestCase):

    def setUp(self):
        """Готовим услуги и мастеров для тестов расписания и связей."""
        # Создаем пул из 15 услуг
        self.services_pool = [
            Service.objects.create(name=f'Услуга {i}', price=1000.00, duration=timedelta(hours=1))
            for i in range(1, 16)
        ]
        self.masters = []
        for i in range(1, 4):
            # ОБЯЗАТЕЛЬНО передаем уникальный email, так как поле уникально в БД
            user = User.objects.create(
                username=f'b_master_{i}',
                email=f'b_master_{i}@example.com',
                role='master'
            )
            self.masters.append(Master.objects.get(user=user))

    def test_assign_overlapping_services(self):
        """Проверяем ManyToMany связь распределения услуг."""
        for index, master in enumerate(self.masters):
            master.services.add(*self.services_pool[index : index + 10])

        for master in self.masters:
            self.assertEqual(master.services.count(), 10)
        self.assertEqual(Service.objects.count(), 15)

    def test_working_hours_mixin_validation(self):
        """Тестируем ваш WorkingHoursMixin (начало работы позже конца)."""
        invalid_schedule = WorkSchedule(
            master=self.masters[0],  # Передаем конкретный инстанс Мастера, а не список
            day_of_week=0,
            start_time=time(18, 0),
            end_time=time(9, 0),
            is_working=True
        )
        with self.assertRaises(ValidationError):
            invalid_schedule.full_clean()

    def test_past_date_exception_denied(self):
        """Тестируем вашу кастомную валидацию даты в ScheduleException.clean()."""
        yesterday = timezone.localdate() - timedelta(days=1)
        past_exception = ScheduleException(
            master=self.masters[0],
            date=yesterday,
            is_working=False,
            reason="Прошлое"
        )
        with self.assertRaises(ValidationError) as context:
            past_exception.full_clean()

        self.assertIn('date', context.exception.message_dict)

    def test_cascade_delete_flow(self):
        """Проверяем каскадное удаление (Услуга должна жить при удалении юзера)."""
        # Создаем отдельного пользователя с уникальным email
        user = User.objects.create(
            username='delete_test_user',
            email='delete_test_user@example.com',
            role='master'
        )
        master = Master.objects.get(user=user)
        # Берем ОДНУ конкретную услугу из пула
        service = self.services_pool[0]

        master.services.add(service)
        WorkSchedule.objects.create(master=master, day_of_week=2, is_working=True)

        user_pk = user.pk
        master_pk = master.pk
        service_pk = service.pk

        user.delete()

        self.assertFalse(User.objects.filter(pk=user_pk).exists())
        self.assertFalse(Master.objects.filter(pk=master_pk).exists())
        self.assertTrue(Service.objects.filter(pk=service_pk).exists())
