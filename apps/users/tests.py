from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from apps.users.forms import RegistrationForm

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

    # ==================== ТЕСТЫ ВЬЮХ И ФОРМ ====================

    def test_registration_form_and_successful_view_post(self):
        """Тест формы и вьюхи: успешная регистрация нового уникального пользователя"""

        form_data = {
            'username': 'Unique_New_User_999',
            'email': 'unique_new_email@example.com',
            'phone': '+79991112233',
            'password1': 'ValidPassword123',
            'password2': 'ValidPassword123',
        }

        # 1. Валидация на уровне формы
        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

        # 2. Валидация на уровне вьюхи при POST запросе
        response = self.client.post(reverse('users:register'), data=form_data)

        # Ожидаем редирект на страницу авторизации
        self.assertRedirects(response, reverse('users:login'))

        # Проверяем, что счетчик пользователей увеличился (стало 101)
        self.assertEqual(User.objects.all().count(), 101)
        self.assertTrue(User.objects.filter(username='Unique_New_User_999').exists())

        # Проверяем запись сообщения об успехе
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Регистрация прошла успешно! Теперь войдите.')

    def test_registration_form_duplicate_email_error(self):
        """Тест формы: блокировка регистрации, если email уже занят одним из 100 пользователей"""

        # Берем email одного из пользователей, созданных в setUp (например, User_50)
        duplicate_email = 'email_50@example.com'

        form_data = {
            'username': 'completely_new_username',
            'email': duplicate_email.upper(),  # Проверяем перевод в нижний регистр clean_email()
            'password1': 'ValidPassword123',
            'password2': 'ValidPassword123',
        }

        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'][0], 'Пользователь с таким email уже зарегистрирован.')

    def test_authenticated_user_cannot_access_register_view(self):
        """Тест вьюхи: авторизованный клиент принудительно перенаправляется с регистрации на 'home'"""

        # Берем 50-го пользователя из setUp и принудительно логиним его
        client_user = User.objects.get(username='User_50')
        self.client.force_login(client_user)

        response = self.client.get(reverse('users:register'))
        self.assertRedirects(response, reverse('users:profile'))

    def test_profile_view_access_control(self):
        """Тест вьюхи: аноним отправляется на логин, авторизованный успешно видит профиль"""

        url = reverse('users:profile')

        # 1. Проверка для анонимного пользователя
        response_anon = self.client.get(url)
        self.assertEqual(response_anon.status_code, 302)
        self.assertIn(reverse('users:login'), response_anon.url)

        # 2. Проверка для авторизованного пользователя
        client_user = User.objects.get(username='User_51')
        self.client.force_login(client_user)

        response_auth = self.client.get(url)
        self.assertEqual(response_auth.status_code, 200)
        self.assertTemplateUsed(response_auth, 'users/profile.html')
