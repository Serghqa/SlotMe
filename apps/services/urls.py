from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.service_list_view, name='service_list'),
    path('master/<int:master_id>/', views.services_by_master_view, name='master_services'),
]
