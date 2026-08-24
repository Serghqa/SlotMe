from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


User = get_user_model()
Service = apps.get_model('services', 'Service')
Master = apps.get_model('masters', 'Master')


class MasterCreationForm(forms.Form):
    email = forms.EmailField(
        label='Электронная почта',
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'placeholder': 'example@mail.com',
            'class': 'form-control',
        })
    )
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()

        user = User.objects.filter(email=email).first()
        if not user:
            raise ValidationError('Пользователя с таким адресом электронной почты не существует.')

        if user.appointments.exists():
            raise ValidationError('Это активный пользователь сервиса.')

        if user.is_admin:
            raise ValidationError('Администратора нельзя сделать мастером.')

        if Master.objects.filter(user=user).exists():
            raise ValidationError(f'Мастер с почтой {email} уже существует.')

        self.cleaned_user = user
        return email

    def save(self):
        master = Master.objects.create(user=self.cleaned_user)
        services = self.cleaned_data.get('services')
        if services:
            master.services.set(services)

        return master
