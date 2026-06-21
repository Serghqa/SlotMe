from datetime import time, timedelta, datetime, date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError, transaction

User = get_user_model()
Master = apps.get_model('masters', 'Master')
Service = apps.get_model('services', 'Service')
Appointment = apps.get_model('appointments', 'Appointment')
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
            role='client',
            phone='+79990000001'
        )
        self.master_user = User.objects.create(
            username='test_master',
            email='master@example.com',
            role='master',
            phone='+79990000002'
        )
        self.master = Master.objects.get(user=self.master_user)

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

    # def test_inactive_master_denied(self):
    #     """Запрет записи к неактивному мастеру"""
    #     self.master.is_active = False
    #     self.master.save()

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_inactive_service_denied(self):
    #     """Запрет записи на неактивную услугу"""
    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.inactive_service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_master_does_not_provide_service_denied(self):
    #     """Запрет записи на услугу, которую мастер не оказывает"""
    #     other_service = Service.objects.create(
    #         name='Массаж',
    #         price=2000.00,
    #         duration=timedelta(hours=1)
    #     )
    #     # Не добавляем услугу мастеру

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=other_service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # # ==================== ПРОВЕРКИ ВРЕМЕНИ ====================

    # def test_past_time_denied(self):
    #     """Запрет записи на прошедшее время"""
    #     past_time = timezone.localtime() - timedelta(hours=2)

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=past_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_non_working_day_denied(self):
    #     """Запрет записи в нерабочий день (суббота)"""
    #     saturday = self.monday + timedelta(days=5)
    #     booking_time = timezone.make_aware(
    #         datetime.combine(saturday, time(10, 0))
    #     )

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=booking_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_outside_working_hours_denied(self):
    #     """Запрет записи вне рабочих часов"""
    #     booking_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(8, 0))
    #     )

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=booking_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_booking_ending_after_closing_denied(self):
    #     """Запрет записи, заканчивающейся после закрытия"""
    #     booking_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(17, 30))
    #     )

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=booking_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_booking_exactly_at_opening_allowed(self):
    #     """Запись ровно на открытие разрешена"""
    #     booking_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(9, 0))
    #     )

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=booking_time,
    #         status='booked'
    #     )
    #     try:
    #         appointment.full_clean()
    #     except ValidationError:
    #         self.fail('Запись ровно на открытие должна быть разрешена')

    # def test_booking_ending_at_closing_allowed(self):
    #     """Запись, заканчивающаяся ровно в закрытие, разрешена"""
    #     booking_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(17, 0))
    #     )

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=booking_time,
    #         status='booked'
    #     )
    #     try:
    #         appointment.full_clean()
    #     except ValidationError:
    #         self.fail('Запись с окончанием в закрытие должна быть разрешена')

    # # ==================== ИСКЛЮЧЕНИЯ РАСПИСАНИЯ ====================

    # def test_day_off_exception_overrides_schedule(self):
    #     """Исключение-выходной имеет приоритет над регулярным расписанием"""
    #     ScheduleException.objects.create(
    #         master=self.master,
    #         date=self.monday,
    #         is_working=False,
    #         reason='Санитарный день'
    #     )

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError) as context:
    #         appointment.full_clean()
    #     self.assertIn('Санитарный день', str(context.exception))

    # def test_short_day_exception_overrides_schedule(self):
    #     """Исключение с коротким днём ограничивает запись"""
    #     ScheduleException.objects.create(
    #         master=self.master,
    #         date=self.monday,
    #         is_working=True,
    #         start_time=time(10, 0),
    #         end_time=time(14, 0),
    #         reason='Короткий день'
    #     )

    #     # Запись вне короткого дня — запрещена
    #     early_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(9, 0))
    #     )
    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=early_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    #     # Запись внутри короткого дня — разрешена
    #     valid_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(11, 0))
    #     )
    #     appointment.start_datetime = valid_time
    #     try:
    #         appointment.full_clean()
    #     except ValidationError:
    #         self.fail('Запись внутри короткого дня должна быть разрешена')

    # def test_exception_makes_day_off_working(self):
    #     """Исключение может сделать выходной день рабочим"""
    #     saturday = self.monday + timedelta(days=5)
    #     ScheduleException.objects.create(
    #         master=self.master,
    #         date=saturday,
    #         is_working=True,
    #         start_time=time(10, 0),
    #         end_time=time(16, 0)
    #     )

    #     booking_time = timezone.make_aware(
    #         datetime.combine(saturday, time(12, 0))
    #     )
    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=booking_time,
    #         status='booked'
    #     )
    #     try:
    #         appointment.full_clean()
    #     except ValidationError:
    #         self.fail('Исключение должно сделать выходной день рабочим')

    # # ==================== ПЕРЕСЕЧЕНИЯ ЗАПИСЕЙ ====================

    # def test_exact_overlap_denied(self):
    #     """Запрет точного наложения на существующую запись"""
    #     Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )

    #     duplicate = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         duplicate.full_clean()

    # def test_partial_overlap_start_denied(self):
    #     """Запрет частичного пересечения в начале"""
    #     # Существующая: 10:00-11:00
    #     Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )

    #     # Новая: 9:30-10:30
    #     overlap_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(9, 30))
    #     )
    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=overlap_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_partial_overlap_end_denied(self):
    #     """Запрет частичного пересечения в конце"""
    #     # Существующая: 10:00-11:00
    #     Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )

    #     # Новая: 10:30-11:30
    #     overlap_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(10, 30))
    #     )
    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=overlap_time,
    #         status='booked'
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_adjacent_no_overlap_allowed(self):
    #     """Запись впритык разрешена (без промежутка)"""
    #     # Первая: 10:00-11:00
    #     Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )

    #     # Вторая: 11:00-12:00
    #     adjacent_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(11, 0))
    #     )
    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=adjacent_time,
    #         status='booked'
    #     )
    #     try:
    #         appointment.full_clean()
    #     except ValidationError:
    #         self.fail('Запись впритык должна быть разрешена')

    # def test_cancelled_appointment_not_blocking(self):
    #     """Отмененная запись не блокирует время"""
    #     Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='cancelled'
    #     )

    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     try:
    #         appointment.full_clean()
    #     except ValidationError:
    #         self.fail('Отмененная запись не должна блокировать время')

    # def test_different_masters_same_time_allowed(self):
    #     """Разные мастера могут иметь записи на одно время"""
    #     # Второй мастер
    #     master2_user = User.objects.create(
    #         username='master2',
    #         email='master2@example.com',
    #         role='master',
    #         phone='+79990000003'
    #     )
    #     master2 = Master.objects.get(user=master2_user)
    #     master2.services.add(self.service)
    #     WorkSchedule.objects.create(
    #         master=master2,
    #         day_of_week=self.monday.weekday(),
    #         start_time=time(9, 0),
    #         end_time=time(18, 0),
    #         is_working=True
    #     )

    #     # Запись к первому мастеру
    #     Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )

    #     # Запись ко второму на то же время — разрешена
    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=master2,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     try:
    #         appointment.full_clean()
    #     except ValidationError:
    #         self.fail('Разные мастера могут работать одновременно')

    # # ==================== СТАТУСЫ И ПЕРЕХОДЫ ====================

    # def test_new_appointment_must_be_booked(self):
    #     """Новая запись может быть только в статусе booked"""
    #     appointment = Appointment(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='completed'  # Нельзя для новой
    #     )
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_cannot_change_final_status_to_booked(self):
    #     """Нельзя изменить финальный статус обратно на booked"""
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='completed'
    #     )

    #     appointment.status = 'booked'
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_cannot_change_cancelled_status(self):
    #     """Нельзя изменить статус отмененной записи"""
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='cancelled'
    #     )

    #     appointment.status = 'booked'
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_cannot_complete_future_appointment(self):
    #     """Нельзя завершить будущую запись"""
    #     future_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(14, 0))
    #     )
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=future_time,
    #         status='booked'
    #     )

    #     appointment.status = 'completed'
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_cannot_no_show_future_appointment(self):
    #     """Нельзя отметить неявку для будущей записи"""
    #     future_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(14, 0))
    #     )
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=future_time,
    #         status='booked'
    #     )

    #     appointment.status = 'no_show'
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # def test_cancel_future_appointment_allowed(self):
    #     """Отменить будущую запись можно"""
    #     future_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(14, 0))
    #     )
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=future_time,
    #         status='booked'
    #     )

    #     appointment.status = 'cancelled'
    #     appointment.cancel_reason = 'Передумал'
    #     try:
    #         appointment.full_clean()
    #         appointment.save()
    #     except ValidationError:
    #         self.fail('Отмена будущей записи должна быть разрешена')

    #     self.assertEqual(appointment.status, 'cancelled')
    #     self.assertIsNotNone(appointment.cancelled_at)

    # def test_cannot_complete_before_end_time(self):
    #     """Нельзя завершить запись до её окончания"""
    #     now = timezone.localtime()
    #     # Создаем запись, которая прямо сейчас в процессе
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=now - timedelta(minutes=30),
    #         status='booked'
    #     )

    #     appointment.status = 'completed'
    #     with self.assertRaises(ValidationError):
    #         appointment.full_clean()

    # # ==================== РЕДАКТИРОВАНИЕ ЗАПИСЕЙ ====================

    # def test_edit_ignores_own_overlap(self):
    #     """При редактировании запись не конфликтует сама с собой"""
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )

    #     # Меняем только услугу, время то же
    #     appointment.service = self.long_service
    #     try:
    #         appointment.full_clean()
    #     except ValidationError:
    #         self.fail('Редактирование своей записи не должно давать конфликт')

    # def test_edit_to_occupied_time_denied(self):
    #     """Редактирование на занятое время запрещено"""
    #     # Первая запись: 10:00-11:00
    #     Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )

    #     # Вторая запись: 14:00-15:00
    #     second_time = timezone.make_aware(
    #         datetime.combine(self.monday, time(14, 0))
    #     )
    #     second = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=second_time,
    #         status='booked'
    #     )

    #     # Пытаемся перенести вторую на 10:00 (где уже есть первая)
    #     second.start_datetime = self.booking_time
    #     with self.assertRaises(ValidationError):
    #         second.full_clean()

    # # ==================== ОГРАНИЧЕНИЯ БД ====================

    # def test_unique_active_booking_constraint(self):
    #     """Уникальность активной записи мастера на время"""
    #     Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )

    #     with self.assertRaises(IntegrityError):
    #         with transaction.atomic():
    #             Appointment.objects.create(
    #                 client=self.client_user,
    #                 master=self.master,
    #                 service=self.service,
    #                 start_datetime=self.booking_time,
    #                 status='booked'
    #             )

    # def test_cancelled_no_unique_constraint(self):
    #     """Отмененная запись не мешает UniqueConstraint"""
    #     Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='cancelled'
    #     )

    #     # Можно создать активную на то же время
    #     try:
    #         Appointment.objects.create(
    #             client=self.client_user,
    #             master=self.master,
    #             service=self.service,
    #             start_datetime=self.booking_time,
    #             status='booked'
    #         )
    #     except IntegrityError:
    #         self.fail('Отмененная запись не должна вызывать IntegrityError')

    # # ==================== СВОЙСТВА МОДЕЛИ ====================

    # def test_is_past_property(self):
    #     """Свойство is_past корректно определяет прошедшие записи"""
    #     past_time = timezone.localtime() - timedelta(hours=2)
    #     past_appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=past_time,
    #         status='booked'
    #     )
    #     self.assertTrue(past_appointment.is_past)

    #     future_appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     self.assertFalse(future_appointment.is_past)

    # def test_can_be_cancelled_property(self):
    #     """Свойство can_be_cancelled работает корректно"""
    #     # Будущая бронь — можно отменить
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     self.assertTrue(appointment.can_be_cancelled)

    #     # Прошедшая — нельзя
    #     past_time = timezone.localtime() - timedelta(hours=2)
    #     past_appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=past_time,
    #         status='booked'
    #     )
    #     self.assertFalse(past_appointment.can_be_cancelled)

    #     # Завершенная — нельзя
    #     completed = appointment
    #     completed.status = 'completed'
    #     completed.save()
    #     self.assertFalse(completed.can_be_cancelled)

    # def test_end_datetime_auto_calculation(self):
    #     """Автоматический расчет end_datetime при создании"""
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         status='booked'
    #     )
    #     expected_end = self.booking_time + self.service.duration
    #     self.assertEqual(appointment.end_datetime, expected_end)

    # def test_manual_end_datetime_not_overwritten(self):
    #     """Ручное end_datetime не перезаписывается"""
    #     custom_end = self.booking_time + timedelta(hours=2)
    #     appointment = Appointment.objects.create(
    #         client=self.client_user,
    #         master=self.master,
    #         service=self.service,
    #         start_datetime=self.booking_time,
    #         end_datetime=custom_end,
    #         status='booked'
    #     )
    #     self.assertEqual(appointment.end_datetime, custom_end)
