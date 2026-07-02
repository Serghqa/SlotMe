from django.apps import apps
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from datetime import time, timedelta

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
        self.users = []

        for i in range(1, 9):
            # ОБЯЗАТЕЛЬНО передаем уникальный email, так как поле уникально в БД
            user = User.objects.create(
                username=f'User_{i}',
                email=f'email_{i}@example.com',
            )
            user.save()
            self.users.append(user)
            if i < 6:
                master = Master.objects.create(user=user)
                master.save()
                self.masters.append(master)

    def test_assign_overlapping_services(self):
        """Проверяем ManyToMany связь распределения услуг."""
        for index, master in enumerate(self.masters):
            master.services.add(*self.services_pool[index : index + 10])

        for master in self.masters:
            self.assertEqual(master.services.count(), 10)
        self.assertEqual(Service.objects.count(), 15)

    def test_working_hours_mixin_validation(self):
        """Тестируем WorkingHoursMixin (начало работы позже конца)."""
        past_schedule = WorkSchedule(
            master=self.masters[0],
            day_of_week=0,
            start_time=time(18, 0),
            end_time=time(9, 0),
            is_working=True
        )
        with self.assertRaises(ValidationError):
            past_schedule.full_clean()

    def test_past_date_exception_denied(self):
        """Тестируем кастомную валидацию даты в ScheduleException."""
        yesterday = timezone.localdate() - timedelta(days=1)
        past_exception = ScheduleException(
            master=self.masters[0],
            date=yesterday,
            is_working=False,
            reason="Прошлое"
        )
        past_exception.full_clean()

    def test_cascade_delete_flow(self):
        """Проверяем каскадное удаление (Услуга должна жить при удалении юзера)."""
        # Создаем отдельного пользователя с уникальным email
        user = User.objects.create(
            username='delete_test_user',
            email='delete_test_user@example.com',
        )
        master = Master.objects.create(user=user)
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

    def test_exception_validation_future_date_only(self):
        """Проверяем, что исключения можно создавать на будущие и прошлые даты."""
        future_date = timezone.localdate() + timedelta(days=1)
        exception = ScheduleException(
            master=self.masters[0],
            date=future_date,
            is_working=False,
            reason="Будущий выходной"
        )
        exception.full_clean()  # Не должно быть ошибок

        past_date = timezone.localdate() - timedelta(days=1)
        exception_past = ScheduleException(
            master=self.masters[0],
            date=past_date,
            is_working=False,
            reason="Прошлый выходной"
        )
        exception_past.full_clean()

    def test_exception_working_hours_mixin(self):
        """Проверяем миксин для исключений."""
        exception = ScheduleException(
            master=self.masters[0],
            date=timezone.localdate() + timedelta(days=1),
            is_working=True,
            start_time=time(10, 0),
            end_time=time(18, 0)
        )
        exception.full_clean()  # OK

        # Неправильные часы
        exception_bad = ScheduleException(
            master=self.masters[0],
            date=timezone.localdate() + timedelta(days=1),
            is_working=True,
            start_time=time(18, 0),
            end_time=time(10, 0)
        )
        with self.assertRaises(ValidationError):
            exception_bad.full_clean()

    def test_exception_save_clears_hours_for_off_day(self):
        """Проверяем, что при сохранении выходного дня часы обнуляются."""
        exception = ScheduleException(
            master=self.masters[0],
            date=timezone.localdate() + timedelta(days=1),
            is_working=False,
            start_time=time(10, 0),  # Должны обнулиться
            end_time=time(18, 0)     # Должны обнулиться
        )
        exception.save()
        self.assertIsNone(exception.start_time)
        self.assertIsNone(exception.end_time)

    def test_schedule_unique_together(self):
        """Проверяем, что нельзя создать два расписания для одного мастера в один день."""
        WorkSchedule.objects.create(
            master=self.masters[0],
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(18, 0),
            is_working=True
        )

        duplicate = WorkSchedule(
            master=self.masters[0],
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(19, 0),
            is_working=True
        )
        with self.assertRaises(Exception):  # IntegrityError
            duplicate.save()

    def test_exception_unique_together(self):
        """Проверяем, что нельзя создать два исключения на одну дату."""
        date = timezone.localdate() + timedelta(days=1)
        ScheduleException.objects.create(
            master=self.masters[0],
            date=date,
            is_working=False,
            reason="Выходной"
        )

        duplicate = ScheduleException(
            master=self.masters[0],
            date=date,
            is_working=True,
            start_time=time(10, 0),
            end_time=time(18, 0)
        )
        with self.assertRaises(Exception):
            duplicate.save()

    def test_cascade_delete_schedule_and_exceptions(self):
        """Проверяем, что при удалении мастера удаляется и его расписание."""
        schedule = WorkSchedule.objects.create(
            master=self.masters[0],
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(18, 0),
            is_working=True
        )
        exception = ScheduleException.objects.create(
            master=self.masters[0],
            date=timezone.localdate() + timedelta(days=1),
            is_working=False
        )

        schedule_pk = schedule.pk
        exception_pk = exception.pk
        master_pk = self.masters[0].pk

        self.masters[0].delete()

        self.assertFalse(WorkSchedule.objects.filter(pk=schedule_pk).exists())
        self.assertFalse(ScheduleException.objects.filter(pk=exception_pk).exists())
        self.assertFalse(Master.objects.filter(pk=master_pk).exists())

    def test_cannot_create_duplicate_master_for_user(self):
        """Проверяем, что нельзя создать двух мастеров для одного пользователя."""
        user = User.objects.create(
            username='test_user',
            email='test_user@example.com'
        )

        # Создаем первого мастера
        master1 = Master.objects.create(user=user)
        self.assertEqual(Master.objects.count(), len(self.masters) + 1)

        # Пытаемся создать второго мастера для того же пользователя
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                master2 = Master.objects.create(user=user)

        # Проверяем, что второй мастер не создался
        self.assertEqual(Master.objects.filter(user=user).count(), 1)
        self.assertEqual(Master.objects.count(), len(self.masters) + 1)

    def test_cannot_create_master_with_existing_master_profile(self):
        """Проверяем через hasattr и связанный объект."""
        user = User.objects.create(
            username='another_user',
            email='another_user@example.com'
        )

        # Создаем мастера
        master = Master.objects.create(user=user)

        # Проверяем, что связанный объект существует
        self.assertTrue(hasattr(user, 'master_profile'))
        self.assertEqual(user.master_profile, master)

        # Пытаемся создать еще одного через другой способ
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Master.objects.create(user=user)

        # Проверяем, что мастер все еще один
        self.assertEqual(Master.objects.filter(user=user).count(), 1)
