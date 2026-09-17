from django.apps import apps
from django.test import TestCase
from datetime import timedelta


Service = apps.get_model('services', 'Service')

class ServiceTestCase(TestCase):

    def setUp(self):
        """Создание тестовых данных для модели Service."""
        for i in range(1, 6):
            Service.objects.create(
                name=f'Service {i}',
                description=f'Description for Service {i}',
                price=10.0 * i,
                duration=timedelta(hours=i),
                is_active=True
            )

    def test_service_str_method(self):
        """Тестирование метода __str__ модели Service."""
        for service in Service.objects.all():
            expected_str = f"{service.name} — {service.price}₽ ({service.duration})"
            self.assertEqual(str(service), expected_str)

    def test_service_duration_validation(self):
        """Тестирование валидации длительности услуги."""
        service = Service(
            name='Invalid Service',
            description='This service has invalid duration.',
            price=50.0,
            duration=timedelta(hours=-1),  # Неверная длительность
            is_active=True
        )
        with self.assertRaises(Exception) as context:
            service.full_clean()  # Проверка валидации модели

        self.assertIn('Длительность должна быть больше нуля.', str(context.exception))
