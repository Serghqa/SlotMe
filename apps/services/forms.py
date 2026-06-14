from django import forms
from .models import Service
from .utils import ServiceValidationMixin


class ServiceForm(ServiceValidationMixin, forms.ModelForm):
    class Meta:
        model = Service
        fields = '__all__'
