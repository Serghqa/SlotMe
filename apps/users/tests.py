from django.test import TestCase
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()
Master = apps.get_model('masters', 'Master')

class UserWorkflowTestCase(TestCase):

    def setUp(self):
        """Выполняется ПЕРЕД КАЖДЫМ тестом в этом классе."""
        # Шаг 1: Создаем 100 клиентов разом через bulk_create (метод save() НЕ вызывается)
        clients_pool = [
            User(
                username=f'bulk_client_{i}',
                email=f'client_{i}@example.com',
                role='client',
                phone=f'+7999000{i:04d}'
            )
            for i in range(1, 101)
        ]
        User.objects.bulk_create(clients_pool)

        # Шаг 2: Создаем 10 мастеров по одному (метод save() ВЫЗЫВАЕТСЯ)
        for i in range(1, 11):
            User.objects.create(
                username=f'individual_master_{i}',
                email=f'master_{i}@example.com',
                role='master',
                phone=f'+7999111{i:04d}'
            )

    def test_initial_creation_state(self):
        """Проверяем базовое корректное создание из setUp."""
        # Проверяем, что 100 клиентов создались разом
        self.assertEqual(User.objects.filter(role='client').count(), 100)

        # Проверяем, что 10 мастеров создались и у них отработал метод save()
        self.assertEqual(User.objects.filter(role='master').count(), 10)
        self.assertEqual(Master.objects.filter(is_active=True).count(), 10)

    def test_upgrade_clients_to_masters(self):
        """Проверяем кастомную бизнес-логику метода save() при апгрейде клиента."""
        clients_to_upgrade = User.objects.filter(role='client')[:10]

        for client in list(clients_to_upgrade):
            client.role = 'master'
            client.save()  # Должен сработать метод save() и создаться профиль Master

        self.assertEqual(User.objects.filter(role='client').count(), 90)
        self.assertEqual(User.objects.filter(role='master').count(), 20)
        self.assertEqual(Master.objects.filter(is_active=True).count(), 20)

    def test_deactivate_upgraded_masters(self):
        """Проверяем кастомную бизнес-логику деактивации профилей мастеров."""
        clients_to_modify = list(User.objects.filter(role='client')[:10])
        for user in clients_to_modify:
            user.role = 'master'
            user.save()

        # Меняем роль этим же 10 пользователям обратно на 'client'
        for user in clients_to_modify:
            user.refresh_from_db()
            user.role = 'client'
            user.save()

        self.assertEqual(User.objects.filter(role='client').count(), 100)
        self.assertEqual(User.objects.filter(role='master').count(), 10)
        self.assertEqual(Master.objects.filter(is_active=True).count(), 10)
        self.assertEqual(Master.objects.filter(is_active=False).count(), 10)
