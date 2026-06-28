from datetime import time, timedelta, datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError, transaction
from zoneinfo import ZoneInfo
from .models import Appointment

User = get_user_model()
Master = apps.get_model('masters', 'Master')
Service = apps.get_model('services', 'Service')
WorkSchedule = apps.get_model('masters', 'WorkSchedule')
ScheduleException = apps.get_model('masters', 'ScheduleException')


class AppointmentBookingTestCase(TestCase):
    """Тесты создания и валидации записей"""

    def setUp(self):
        """Создаем базовое окружение для тестов"""
        # Пользователи
        self.client_user = User.objects.create(
            username='test_client',
            email='client@example.com',
            phone='+79990000001'
        )
        self.master_user = User.objects.create(
            username='test_master',
            email='master@example.com',
            phone='+79990000002'
        )
        self.master = Master.objects.create(user=self.master_user)

        # Услуги
        self.service = Service.objects.create(
            name='Стрижка',
            price=1500.00,
            duration=timedelta(hours=1)
        )
        self.long_service = Service.objects.create(
            name='Окрашивание',
            price=5000.00,
            duration=timedelta(hours=3)
        )
        self.inactive_service = Service.objects.create(
            name='Архивная услуга',
            price=500.00,
            duration=timedelta(minutes=30),
            is_active=False
        )
        self.master.services.add(self.service, self.long_service, self.inactive_service)

        # Дата для тестов — ближайший понедельник
        now = timezone.localtime()
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # следующий понедельник
        self.monday = now.date() + timedelta(days=days_until_monday)

        # Расписание на каждый день недели
        for day in range(7):
            is_working = day < 5  # Пн-Пт рабочие
            WorkSchedule.objects.create(
                master=self.master,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(18, 0),
                is_working=is_working
            )

        # Стандартное время для записи
        self.booking_time = timezone.make_aware(
            datetime.combine(self.monday, time(10, 0))
        )

    # ==================== БАЗОВАЯ ВАЛИДАЦИЯ ====================

    def test_valid_booking_creates_appointment(self):
        """Успешное создание записи с корректными данными"""
        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )

        appointment.full_clean()
        appointment.save()
        self.assertIsNotNone(appointment.pk)
        self.assertEqual(appointment.status, 'booked')
        self.assertEqual(
            appointment.end_datetime,
            self.booking_time + self.service.duration
        )

    def test_inactive_master_denied(self):
        """Запрет записи к неактивному мастеру"""
        self.master.is_active = False
        self.master.save()

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_inactive_service_denied(self):
        """Запрет записи на неактивную услугу"""
        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.inactive_service,
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_master_does_not_provide_service_denied(self):
        """Запрет записи на услугу, которую мастер не оказывает"""
        other_service = Service.objects.create(
            name='Массаж',
            price=2000.00,
            duration=timedelta(hours=1)
        )
        # Не добавляем услугу мастеру

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=other_service,
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_missing_required_fields_denied(self):
        """Пропуск обязательных полей вызывает ошибку валидации"""
        appointment = Appointment(
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_master_without_schedule_denied(self):
        """Запись к мастеру без расписания запрещена"""
        user_master = User.objects.create(
            username='user_master_no_schedule',
            email='nosched@example.com',
            phone='+79990000006'
        )
        master_no_schedule = Master.objects.create(user=user_master)
        master_no_schedule.services.add(self.service)

        appointment = Appointment(
            client=self.client_user,
            master=master_no_schedule,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    # # ==================== ПРОВЕРКИ ВРЕМЕНИ ====================

    def test_past_time_denied(self):
        """Запрет записи на прошедшее время"""
        past_time = timezone.localtime() - timedelta(hours=2)

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=past_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_non_working_day_denied(self):
        """Запрет записи в нерабочий день (суббота)"""
        saturday = self.monday + timedelta(days=5)
        booking_time = timezone.make_aware(
            datetime.combine(saturday, time(10, 0))
        )

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_outside_working_hours_denied(self):
        """Запрет записи вне рабочих часов"""
        booking_time = timezone.make_aware(
            datetime.combine(self.monday, time(8, 0))
        )

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_booking_ending_after_closing_denied(self):
        """Запрет записи, заканчивающейся после закрытия"""
        booking_time = timezone.make_aware(
            datetime.combine(self.monday, time(17, 30))
        )

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_booking_exactly_at_opening_allowed(self):
        """Запись ровно на открытие разрешена"""
        booking_time = timezone.make_aware(
            datetime.combine(self.monday, time(9, 0))
        )

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=booking_time,
            status='booked'
        )
        try:
            appointment.full_clean()
        except ValidationError:
            self.fail('Запись ровно на открытие должна быть разрешена')

    def test_booking_ending_at_closing_allowed(self):
        """Запись, заканчивающаяся ровно в закрытие, разрешена"""
        booking_time = timezone.make_aware(
            datetime.combine(self.monday, time(17, 0))
        )

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=booking_time,
            status='booked'
        )
        try:
            appointment.full_clean()
        except ValidationError:
            self.fail('Запись с окончанием в закрытие должна быть разрешена')

    def test_cannot_set_completed_for_past_appointment_still_in_progress(self):
        """Нельзя завершить запись, которая ещё не закончилась по времени"""
        now = timezone.localtime()
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=now - timedelta(minutes=30),
            status='booked'
        )
        appointment.status = 'completed'
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    # # ==================== ИСКЛЮЧЕНИЯ РАСПИСАНИЯ ====================

    def test_day_off_exception_overrides_schedule(self):
        """Исключение-выходной имеет приоритет над регулярным расписанием"""
        ScheduleException.objects.create(
            master=self.master,
            date=self.monday,
            is_working=False,
            reason='Санитарный день'
        )

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError) as context:
            appointment.full_clean()
        self.assertIn('Санитарный день', str(context.exception))

    def test_short_day_exception_overrides_schedule(self):
        """Исключение с коротким днём ограничивает запись"""
        ScheduleException.objects.create(
            master=self.master,
            date=self.monday,
            is_working=True,
            start_time=time(10, 0),
            end_time=time(14, 0),
            reason='Короткий день'
        )

        # Запись вне короткого дня — запрещена
        early_time = timezone.make_aware(
            datetime.combine(self.monday, time(9, 0))
        )
        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=early_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

        # Запись внутри короткого дня — разрешена
        valid_time = timezone.make_aware(
            datetime.combine(self.monday, time(11, 0))
        )
        appointment.start_datetime = valid_time
        try:
            appointment.full_clean()
        except ValidationError:
            self.fail('Запись внутри короткого дня должна быть разрешена')

    def test_exception_makes_day_off_working(self):
        """Исключение может сделать выходной день рабочим"""
        saturday = self.monday + timedelta(days=5)
        ScheduleException.objects.create(
            master=self.master,
            date=saturday,
            is_working=True,
            start_time=time(10, 0),
            end_time=time(16, 0)
        )

        booking_time = timezone.make_aware(
            datetime.combine(saturday, time(12, 0))
        )
        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=booking_time,
            status='booked'
        )
        try:
            appointment.full_clean()
        except ValidationError:
            self.fail('Исключение должно сделать выходной день рабочим')

    # # ==================== ПЕРЕСЕЧЕНИЯ ЗАПИСЕЙ ====================

    def test_exact_overlap_denied(self):
        """Запрет точного наложения на существующую запись"""
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )

        duplicate = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_partial_overlap_start_denied(self):
        """Запрет частичного пересечения в начале"""
        # Существующая: 10:00-11:00
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )

        # Новая: 9:30-10:30
        overlap_time = timezone.make_aware(
            datetime.combine(self.monday, time(9, 30))
        )
        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=overlap_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_partial_overlap_end_denied(self):
        """Запрет частичного пересечения в конце"""
        # Существующая: 10:00-11:00
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )

        # Новая: 10:30-11:30
        overlap_time = timezone.make_aware(
            datetime.combine(self.monday, time(10, 30))
        )
        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=overlap_time,
            status='booked'
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_adjacent_no_overlap_allowed(self):
        """Запись впритык разрешена (без промежутка)"""
        # Первая: 10:00-11:00
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )

        # Вторая: 11:00-12:00
        adjacent_time = timezone.make_aware(
            datetime.combine(self.monday, time(11, 0))
        )
        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=adjacent_time,
            status='booked'
        )
        try:
            appointment.full_clean()
        except ValidationError:
            self.fail('Запись впритык должна быть разрешена')

    def test_cancelled_appointment_not_blocking(self):
        """Отмененная запись не блокирует время"""
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='cancelled'
        )

        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        try:
            appointment.full_clean()
        except ValidationError:
            self.fail('Отмененная запись не должна блокировать время')

    def test_different_masters_same_time_allowed(self):
        """Разные мастера могут иметь записи на одно время"""
        # Второй мастер
        user_master_2 = User.objects.create(
            username='master2',
            email='master2@example.com',
            phone='+79990000003'
        )
        master2 = Master.objects.create(user=user_master_2)
        master2.services.add(self.service)
        WorkSchedule.objects.create(
            master=master2,
            day_of_week=self.monday.weekday(),
            start_time=time(9, 0),
            end_time=time(18, 0),
            is_working=True
        )

        # Запись к первому мастеру
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )

        # Запись ко второму на то же время — разрешена
        appointment = Appointment(
            client=self.client_user,
            master=master2,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        try:
            appointment.full_clean()
        except ValidationError:
            self.fail('Разные мастера могут работать одновременно')

    # # ==================== СТАТУСЫ И ПЕРЕХОДЫ ====================

    def test_new_appointment_must_be_booked(self):
        """Новая запись может быть только в статусе booked"""
        appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='completed'  # Нельзя для новой
        )
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_cannot_change_final_status_to_booked(self):
        """Нельзя изменить финальный статус обратно на booked"""
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='completed'
        )

        appointment.status = 'booked'
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_cannot_change_cancelled_status(self):
        """Нельзя изменить статус отмененной записи"""
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='cancelled'
        )

        appointment.status = 'booked'
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_cannot_complete_future_appointment(self):
        """Нельзя завершить будущую запись"""
        future_time = timezone.make_aware(
            datetime.combine(self.monday, time(14, 0))
        )
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=future_time,
            status='booked'
        )

        appointment.status = 'completed'
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_cannot_no_show_future_appointment(self):
        """Нельзя отметить неявку для будущей записи"""
        future_time = timezone.make_aware(
            datetime.combine(self.monday, time(14, 0))
        )
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=future_time,
            status='booked'
        )

        appointment.status = 'no_show'
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    def test_cancel_future_appointment_allowed(self):
        """Отменить будущую запись можно"""
        future_time = timezone.make_aware(
            datetime.combine(self.monday, time(14, 0))
        )
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=future_time,
            status='booked'
        )

        appointment.status = 'cancelled'
        appointment.cancel_reason = 'Передумал'
        try:
            appointment.full_clean()
            appointment.save()
        except ValidationError:
            self.fail('Отмена будущей записи должна быть разрешена')

        self.assertEqual(appointment.status, 'cancelled')
        self.assertIsNotNone(appointment.cancelled_at)

    def test_cannot_complete_before_end_time(self):
        """Нельзя завершить запись до её окончания"""
        now = timezone.localtime()
        # Создаем запись, которая прямо сейчас в процессе
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=now - timedelta(minutes=30),
            status='booked'
        )

        appointment.status = 'completed'
        with self.assertRaises(ValidationError):
            appointment.full_clean()

    # # ==================== ОГРАНИЧЕНИЯ БД ====================

    def test_unique_active_booking_constraint(self):
        """Уникальность активной записи мастера на время"""
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(
                    client=self.client_user,
                    master=self.master,
                    service=self.service,
                    start_datetime=self.booking_time,
                    status='booked'
                )

    def test_cancelled_no_unique_constraint(self):
        """Отмененная запись не мешает UniqueConstraint"""
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='cancelled'
        )

        # Можно создать активную на то же время
        try:
            Appointment.objects.create(
                client=self.client_user,
                master=self.master,
                service=self.service,
                start_datetime=self.booking_time,
                status='booked'
            )
        except IntegrityError:
            self.fail('Отмененная запись не должна вызывать IntegrityError')

    def test_zero_duration_service_denied_by_db(self):
        """База данных запрещает услугу с нулевой длительностью"""
        with self.assertRaises(IntegrityError):
            Service.objects.create(
                name='Нулевая',
                price=100,
                duration=timedelta(0)
            )

    def test_negative_duration_service_denied_by_db(self):
        """База данных запрещает услугу с отрицательной длительностью"""
        with self.assertRaises(IntegrityError):
            Service.objects.create(
                name='Отрицательная',
                price=100,
                duration=timedelta(minutes=-30)
            )

    def test_cannot_delete_master_with_appointments(self):
        """Нельзя удалить мастера, у которого есть записи"""
        from django.db.models import ProtectedError
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ProtectedError):
            self.master.delete()

    def test_cannot_delete_service_with_appointments(self):
        """Нельзя удалить услугу, на которую есть записи"""
        from django.db.models import ProtectedError
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ProtectedError):
            self.service.delete()

    def test_cannot_delete_client_with_appointments(self):
        """Нельзя удалить клиента, у которого есть записи"""
        from django.db.models import ProtectedError
        Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        with self.assertRaises(ProtectedError):
            self.client_user.delete()

    # # ==================== СВОЙСТВА МОДЕЛИ ====================

    def test_is_past_property(self):
        """Свойство is_past корректно определяет прошедшие записи"""
        past_time = timezone.localtime() - timedelta(hours=2)
        past_appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=past_time,
            status='booked'
        )
        self.assertTrue(past_appointment.is_past)

        future_appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        self.assertFalse(future_appointment.is_past)

    def test_can_be_cancelled_property(self):
        """Свойство can_be_cancelled работает корректно"""
        # Будущая бронь — можно отменить
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        self.assertTrue(appointment.can_be_cancelled)

        # Прошедшая — нельзя
        past_time = timezone.localtime() - timedelta(hours=2)
        past_appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=past_time,
            status='booked'
        )
        self.assertFalse(past_appointment.can_be_cancelled)

        # Завершенная — нельзя
        completed = appointment
        completed.status = 'completed'
        completed.save()
        self.assertFalse(completed.can_be_cancelled)

    def test_end_datetime_auto_calculation(self):
        """Автоматический расчет end_datetime при создании"""
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            status='booked'
        )
        expected_end = self.booking_time + self.service.duration
        self.assertEqual(appointment.end_datetime, expected_end)

    def test_manual_end_datetime_not_overwritten(self):
        """Ручное end_datetime не перезаписывается"""
        custom_end = self.booking_time + timedelta(hours=2)
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,
            end_datetime=custom_end,
            status='booked'
        )
        self.assertNotEqual(appointment.end_datetime, custom_end)

    def test_cancelled_at_in_utc(self):
        """Проверяем, что cancelled_at сохраняется в UTC."""
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=timezone.now(),
            status='cancelled'
        )

        # Сохраняется с UTC временем
        self.assertEqual(appointment.cancelled_at.tzinfo, timezone.UTC)

    def test_cancelled_at_display_in_local_time(self):
        """Проверяем отображение в локальном времени."""
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=timezone.now(),
            status='cancelled'
        )

        # Конвертируем в Europe/Moscow
        moscow_tz = ZoneInfo('Europe/Moscow')
        local_time = appointment.cancelled_at.astimezone(moscow_tz)

        # Проверяем, что часовой пояс изменился
        self.assertEqual(local_time.tzinfo, moscow_tz)

    def test_cancelled_at_not_set_on_creation(self):
        """При создании записи cancelled_at должен быть None."""
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=timezone.now(),
            status='booked'
        )
        self.assertIsNone(appointment.cancelled_at)

    def test_cancelled_at_set_only_once(self):
        """Проверяем, что cancelled_at не перезаписывается."""
        appointment = Appointment.objects.create(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=timezone.now(),
            status='cancelled'
        )
        first_cancelled = appointment.cancelled_at

        # Ждем немного
        import time
        time.sleep(0.5)

        # Сохраняем еще раз
        appointment.save()

        # cancelled_at не изменился
        self.assertEqual(appointment.cancelled_at, first_cancelled)

    # ==================== ТЕСТЫ ГЕНЕРАЦИИ И ФИЛЬТРАЦИИ СЛОТОВ ====================

    def test_get_available_slots_returns_correct_intervals(self):
        """Проверка базовой генерации слотов в рабочий день по расписанию мастера"""
        from apps.appointments.services import get_available_slots

        # Запрашиваем слоты на рабочий понедельник
        slots = get_available_slots(self.master, self.monday, self.service)

        # Проверяем, что слоты сгенерировались
        self.assertTrue(len(slots) > 0)
        # Первый слот должен совпадать со временем начала работы (09:00)
        self.assertEqual(slots[0], time(9, 0))

    def test_booked_slots_are_excluded_from_available(self):
        """Занятые интервалы времени должны исключаться из доступных слотов"""
        from apps.appointments.services import get_available_slots

        # Создаем существующую запись на 10:00 (длительность 1 час)
        existing_appointment = Appointment(
            client=self.client_user,
            master=self.master,
            service=self.service,
            start_datetime=self.booking_time,  # 10:00
            status='booked'
        )
        existing_appointment.full_clean()
        existing_appointment.save()

        # Получаем свободные слоты на этот же день
        slots = get_available_slots(self.master, self.monday, self.service)

        # Время 10:00 должно быть исключено из доступных окон
        self.assertNotIn(time(10, 0), slots)

    def test_slots_generation_respects_service_duration(self):
        """Слоты в конце рабочего дня не должны создаваться, если услуга не успеет завершиться"""
        from apps.appointments.services import get_available_slots

        # Конец рабочего дня в setUp — 18:00.
        # Для услуги длительностью 1 час (self.service) последний возможный слот — 17:00.
        slots_short = get_available_slots(self.master, self.monday, self.service)
        self.assertIn(time(17, 0), slots_short)
        self.assertNotIn(time(17, 30), slots_short)

        # Для длинной услуги в 3 часа (self.long_service) последний возможный слот — 15:00.
        slots_long = get_available_slots(self.master, self.monday, self.long_service)
        self.assertIn(time(15, 0), slots_long)
        self.assertNotIn(time(16, 0), slots_long)

    def test_weekend_returns_no_slots(self):
        """В выходные дни (согласно WorkSchedule) слоты не должны генерироваться"""
        from apps.appointments.services import get_available_slots

        # Вычисляем ближайшую субботу (следующую за тестовым понедельником)
        saturday = self.monday + timedelta(days=5)

        slots = get_available_slots(self.master, saturday, self.service)
        self.assertEqual(slots, [])

    def test_past_datetime_slots_are_filtered_out_today(self):
        """Если слоты запрашиваются на 'сегодня', уже прошедшие часы должны отсекаться"""
        from apps.appointments.services import get_available_slots
        from unittest.mock import patch

        # Фиксируем текущее локальное время на 14:30 понедельника
        mock_now = timezone.make_aware(
            datetime.combine(self.monday, time(14, 30))
        )

        with patch('django.utils.timezone.localtime', return_value=mock_now), \
             patch('django.utils.timezone.localdate', return_value=self.monday):

            slots = get_available_slots(self.master, self.monday, self.service)

            # Слоты до 14:30 (например, 09:00, 10:00, 14:00) не должны попасть в выдачу
            for slot in slots:
                slot_datetime = timezone.make_aware(datetime.combine(self.monday, slot))
                self.assertGreaterEqual(slot_datetime, mock_now)

    # ==================== ТЕСТЫ ИСКЛЮЧЕНИЙ ИЗ РАСПИСАНИЯ ====================

    def test_schedule_exception_full_day_off_returns_no_slots(self):
        """Исключение типа 'выходной' полностью отменяет генерацию слотов на конкретную дату"""
        from apps.appointments.services import get_available_slots

        # Создаем исключение: в тестовый понедельник мастер берет выходной
        ScheduleException.objects.create(
            master=self.master,
            date=self.monday,
            is_working=False,
            # Время начала и конца не важны, так как день нерабочий
            start_time=None,
            end_time=None
        )

        # Запрашиваем слоты на этот понедельник
        slots = get_available_slots(self.master, self.monday, self.service)

        # Результат должен быть абсолютно пустым, несмотря на регулярный WorkSchedule
        self.assertEqual(slots, [])

    def test_schedule_exception_short_day_overrides_regular_schedule(self):
        """Исключение с измененным временем перезаписывает стандартные часы работы"""
        from apps.appointments.services import get_available_slots

        # Стандартный рабочий день в setUp: 09:00 - 18:00.
        # Создаем исключение: короткий день в понедельник с 12:00 до 15:00
        ScheduleException.objects.create(
            master=self.master,
            date=self.monday,
            is_working=True,
            start_time=time(12, 0),
            end_time=time(15, 0)
        )

        slots = get_available_slots(self.master, self.monday, self.service)

        # Проверяем, что утренние слоты исчезли
        self.assertNotIn(time(9, 0), slots)
        self.assertNotIn(time(11, 0), slots)

        # Проверяем, что слоты генерируются внутри нового окна
        self.assertIn(time(12, 0), slots)
        self.assertIn(time(13, 0), slots)

        # Последний возможный слот для 1-часовой услуги при закрытии в 15:00 — это 14:00
        self.assertIn(time(14, 0), slots)
        self.assertNotIn(time(15, 0), slots)

    def test_schedule_exception_working_day_on_regular_weekend(self):
        """Исключение может сделать регулярный выходной день (например, субботу) рабочим"""
        from apps.appointments.services import get_available_slots, invalidate_slots_cache

        # Вычисляем ближайшую субботу (в setUp она настроена как is_working=False)
        saturday = self.monday + timedelta(days=5)

        # На всякий случай проверяем, что без исключений там пусто
        slots_before = get_available_slots(self.master, saturday, self.service)
        self.assertEqual(slots_before, [])

        # Создаем исключение: рабочая суббота с 10:00 до 14:00
        ScheduleException.objects.create(
            master=self.master,
            date=saturday,
            is_working=True,
            start_time=time(10, 0),
            end_time=time(14, 0)
        )
        # СБРАСЫВАЕМ КЭШ, чтобы функция увидела изменения в БД
        invalidate_slots_cache(self.master, saturday)

        slots_after = get_available_slots(self.master, saturday, self.service)

        # Теперь в субботу должны появиться доступные окна
        self.assertTrue(len(slots_after) > 0)
        self.assertIn(time(10, 0), slots_after)
        self.assertNotIn(time(9, 0), slots_after)
