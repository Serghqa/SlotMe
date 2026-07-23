from django.urls import path
from . import views


app_name = 'masters'


urlpatterns = [
    path('', views.master_list_view, name='master_list'),
    path('<int:master_id>/', views.master_detail_view,  name='master_detail'),
    path('admin/', views.admin_master_list_view, name='admin_list'),
    path('admin/create/', views.admin_master_create_view, name='admin_create'),
    path('admin/<int:master_id>/toggle/', views.admin_master_toggle_active_view, name='admin_toggle'),
    path('admin/<int:master_id>/services', views.admin_master_services, name='admin_services'),
]
