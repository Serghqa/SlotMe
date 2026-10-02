from django.urls import path
from . import views


app_name = 'admin_panel'


urlpatterns = [
    path('masters/', views.master_list_view, name='master_list'),
    path('master/<int:master_id>/services/', views.services_by_master_view, name='master_services'),
    path('appointments/', views.appointment_list_view, name='appointment_list'),
    path('appointment/<int:appointment_id>/update_status/', views.update_appointment_status_view, name='appointment_update_status'),
    path('appointment/<int:appointment_id>/cancel/', views.cancel_appointment_view, name='appointment_cancel'),
]
