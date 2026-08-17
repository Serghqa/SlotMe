from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Email',
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        label='Телефон',
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'phone')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            if User.objects.filter(email=email).exists():
                raise ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email


class UserCreationFormAdmin(UserCreationForm):

    class Meta:
        model = User
        fields = ('email', 'first_name', 'phone')



class UserChangeFormAdmin(UserChangeForm):

    class Meta:
        model = User
        fields = ('email', 'first_name', 'phone', 'is_active', 'is_staff')
