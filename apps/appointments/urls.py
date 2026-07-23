from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('book/<int:master_id>/', views.book_appointment_view, name='book'),
    path('my/', views.client_appointments_view, name='client_list'),
    path('<int:appointment_id>/cancel/', views.client_cancel_appointment_view, name='cancel'),
    path('schedule/', views.master_schedule_view, name='master_schedule'),
    path('<int:appointment_id>/status/', views.master_update_appointment_status_view, name='update_status'),
    path('<int:appointment_id>/master_cancel/', views.master_cancel_appointment_view, name='master_cancel'),
    path('admin/', views.admin_appointments_view, name='admin_list'),
    path('admin/<int:appointment_id>/update_status/', views.admin_update_appointment_status_view, name='admin_update_status'),
    path('admin/<int:appointment_id>/admin_cancel/', views.admin_cancel_appointment_view, name='admin_cancel'),
]
