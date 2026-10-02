from django.urls import path
from . import views


app_name = 'masters'


urlpatterns = [
    path('', views.master_list_view, name='master_list'),
    path('master/<int:master_id>/', views.master_detail_view,  name='master_detail'),
    path('service/<int:service_id>/', views.masters_by_service_view, name='masters_service'),
]
