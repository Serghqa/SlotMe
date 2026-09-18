from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField
from .utils import BootstrapFormMixin
from .models import User


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.EmailField(
        label='Электронная почта',
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'placeholder': 'example@mail.com',
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Введите пароль',
        })
    )


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Электронная почта',
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'placeholder': 'example@mail.com',
        })
    )
    phone = PhoneNumberField(
        required=True,
        label='Телефон',
        widget=forms.TextInput(attrs={
            'placeholder': '+7 (999) 999-99-99',
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Имя',
        widget=forms.TextInput(attrs={
            'placeholder': 'Введите имя',
        })
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'phone')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            if User.objects.filter(email=email).exists():
                raise ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email


class AdminUserCreationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ('email', 'first_name', 'phone')


class AdminUserChangeForm(UserChangeForm):

    class Meta:
        model = User
        fields = ('email', 'first_name', 'phone', 'is_active', 'is_staff')
