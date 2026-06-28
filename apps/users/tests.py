from django.test import TestCase
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()
Master = apps.get_model('masters', 'Master')

class UserWorkflowTestCase(TestCase):

    def setUp(self):
        """Выполняется ПЕРЕД КАЖДЫМ тестом в этом классе."""
        # Шаг 1: Создаем 100 клиентов разом через bulk_create
        clients_pool = [
            User(
                username=f'User_{i}',
                email=f'email_{i}@example.com',
                phone=f'+7999000{i:04d}'
            )
            for i in range(1, 101)
        ]
        User.objects.bulk_create(clients_pool)

        # Шаг 2: Создаем 10 мастеров по одному
        self.users = User.objects.all()
        self.master_users = self.users[:10]
        self.masters = [
            Master.objects.create(
                user=self.master_users[i],
                bio=f'I am {self.master_users[i].username}'
            )
            for i in range(10)
        ]

    def test_initial_creation_state(self):
        """Проверяем базовое корректное создание из setUp."""
        # Проверяем, что 100 клиентов создались разом
        self.assertEqual(User.objects.all().count(), 100)

        # Проверяем, что 10 мастеров создались и у них отработал метод save()
        self.assertEqual(Master.objects.all().count(), 10)
        self.assertEqual(Master.objects.filter(is_active=True).count(), 10)

    def test_deactivate_upgraded_masters(self):
        """Проверяем деактивацию профилей мастеров."""
        # Проверяем деактивацию 5 мастеров
        for master in self.masters[:5]:
            master.is_active = False
            master.save()

        self.assertEqual(User.objects.all().count(), 100)
        self.assertEqual(Master.objects.filter(is_active=True).count(), 5)
        self.assertEqual(Master.objects.filter(is_active=False).count(), 5)

    def test_is_master_property(self):
        """Проверяем свойство модели определения связной модели мастера"""
        self.assertEqual(self.master_users[0].is_master, True)
        self.assertEqual(self.users[15].is_master, False)
