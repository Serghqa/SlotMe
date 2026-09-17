from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from apps.users.forms import RegistrationForm

User = get_user_model()
Master = apps.get_model('masters', 'Master')

class UserTestCase(TestCase):

    def setUp(self):
        """Выполняется ПЕРЕД КАЖДЫМ тестом в этом классе."""
        # Шаг 1: Создаем 20 клиентов

        for i in range(1, 21):
            User.objects.create(
                email=f'email_{i}@example.com',
                phone=f'+7999000{i:04d}',
                first_name=f'user_{i}',
            )

        # Шаг 2: Создаем 10 мастеров
        self.users = User.objects.all()
        self.master_users = self.users[:10]
        self.masters = [
            Master.objects.create(
                user=self.master_users[i],
                bio=f'I am {self.master_users[i].first_name}'
            )
            for i in range(10)
        ]

    def test_initial_creation_state(self):
        """Проверяем базовое корректное создание из setUp."""
        # Проверяем, что 20 клиентов создались
        self.assertEqual(User.objects.all().count(), 20)

        # Проверяем, что 10 мастеров создались и у них отработал метод save()
        self.assertEqual(Master.objects.all().count(), 10)
        self.assertEqual(Master.objects.filter(is_active=True).count(), 10)

    def test_deactivate_upgraded_masters(self):
        """Проверяем деактивацию профилей мастеров."""
        # Проверяем деактивацию 5 мастеров
        for master in self.masters[:5]:
            master.is_active = False
            master.save()

        self.assertEqual(User.objects.all().count(), 20)
        self.assertEqual(Master.objects.filter(is_active=True).count(), 5)
        self.assertEqual(Master.objects.filter(is_active=False).count(), 5)

    def test_is_master_property(self):
        """Проверяем свойство модели определения связной модели мастера"""
        self.assertEqual(self.master_users[0].is_master, True)
        self.assertEqual(self.users[15].is_master, False)

    def test_registration_form_and_successful_view_post(self):
        """Тест формы и вьюхи: успешная регистрация нового уникального пользователя"""

        form_data = {
            'email': 'unique_new_email@example.com',
            'phone': '+79991112233',
            'first_name': 'valide_name',
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

        # Проверяем, что счетчик пользователей увеличился (стало 21)
        self.assertEqual(User.objects.all().count(), 21)
        self.assertTrue(User.objects.filter(email=form_data['email']).exists())

        # Проверяем запись сообщения об успехе
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Регистрация прошла успешно! Теперь войдите.')

    def test_registration_form_duplicate_email_error(self):
        """Тест формы: блокировка регистрации, если email уже занят одним из 20 пользователей"""

        duplicate_email = self.users[0].email

        form_data = {
            'first_name': 'completely_new_name',
            'email': duplicate_email.upper(),  # Проверяем перевод в нижний регистр clean_email()
            'phone': '+79998887766',
            'password1': 'ValidPassword123',
            'password2': 'ValidPassword123',
        }

        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'][0], 'Пользователь с таким email уже зарегистрирован.')

    def test_authenticated_user_cannot_access_register_view(self):
        """Тест вьюхи: авторизованный клиент принудительно перенаправляется с регистрации на 'profile'"""

        user = self.users[0]
        self.client.force_login(user)

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
        user = self.users[0]
        self.client.force_login(user)

        response_auth = self.client.get(url)
        self.assertEqual(response_auth.status_code, 200)
        self.assertTemplateUsed(response_auth, 'users/profile.html')

    def test_user_model_save_normalization(self):
        """Проверяем, что метод save() принудительно нормализует email и форматирует телефон."""
        password = 'ValidPassword123'
        user = User.objects.create_user(
            email='UPPER_case_EMAIL@Example.com',
            phone='8 (999) 111-22-33',
            first_name='Ivan',
            password=password
        )
        # Email должен стать полностью строчным
        self.assertEqual(user.email, 'upper_case_email@example.com')
        # Телефон должен автоматически стать в формате E.164 благодаря PhoneNumberField
        self.assertEqual(user.phone, '+79991112233')

    def test_registration_form_invalid_phone_error(self):
        """Тест формы: блокировка регистрации при некорректном формате телефона."""
        form_data = {
            'email': 'phone_test@example.com',
            'phone': '12345',  # Невалидный номер
            'first_name': 'Test',
            'password1': 'ValidPassword123',
            'password2': 'ValidPassword123',
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_registration_form_phone_normalization(self):
        """Тест формы: успешная регистрация, если телефон введен в национальном формате (с 8-ки)."""
        form_data = {
            'email': 'phone_norm@example.com',
            'phone': '8 (999) 777-66-55',
            'first_name': 'Test',
            'password1': 'ValidPassword123',
            'password2': 'ValidPassword123',
        }
        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Сохраняем форму и проверяем, что в базу улетел чистый международный формат
        user = form.save()
        self.assertEqual(user.phone, '+79997776655')

    def test_authentication_backend_case_insensitivity(self):
        """Тест бэкенда: успешный вход, если email введен в другом регистре."""
        password = 'ValidPassword123'
        # Создаем тестового пользователя
        user = User.objects.create_user(
            email='test_auth@example.com',
            phone='+79995554433',
            first_name='AuthTest',
            password=password
        )

        # Пытаемся залогиниться, используя разные регистры в email
        login_data = {
            'username': 'TEST_AUTH@EXAMPLE.COM',  # Верхний регистр
            'password': password,
        }

        # Проверяем через клиент Django
        response = self.client.post(reverse('users:login'), data=login_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users:profile'))

        # Проверяем, что пользователь действительно авторизован в текущей сессии
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_registration_form_password_mismatch(self):
        """Тест формы: ошибка, если пароли password1 и password2 не совпадают."""
        form_data = {
            'email': 'pass_test@example.com',
            'phone': '+79991112233',
            'first_name': 'Ivan',
            'password1': 'ValidPassword123',
            'password2': 'DifferentPassword123',  # Пароли разные
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_user_string_representation(self):
        """Проверяем строковое отображение пользователя."""
        user = User(first_name='Иван', last_name='Иванов')
        self.assertEqual(str(user), 'Иван Иванов')

        user_only_first = User(first_name='Петр')
        self.assertEqual(str(user_only_first), 'Петр')

    def test_login_disabled_user_fails(self):
        """Тест формы входа: заблокированный пользователь (is_active=False) не может авторизоваться."""
        # 1. Берем пользователя из setUp и деактивируем его аккаунт
        disabled_user = self.users[0]  # Любой пользователь из созданных
        disabled_user.is_active = False
        disabled_user.save()

        # Данные для формы входа
        login_data = {
            'username': disabled_user.email,
            'password': 'TestPassword123',
        }

        # 2. Пытаемся отправить POST-запрос на страницу входа
        response = self.client.post(reverse('users:login'), data=login_data)

        # Ожидаем, что редиректа на профиль НЕ произошло (остаемся на странице логина с кодом 200)
        self.assertEqual(response.status_code, 200)

        # Проверяем, что в контексте формы есть ошибки
        form = response.context['form']
        self.assertFalse(form.is_valid())

        # Django возвращает общую ошибку '__all__' (non_field_errors) для неверных/неактивных аккаунтов
        self.assertIn('__all__', form.errors)

        # 3. Проверяем, что сессия осталась пустой (пользователь не авторизован)
        self.assertNotIn('_auth_user_id', self.client.session)
