from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('book/<int:master_id>/', views.book_appointment_view, name='book'),
    path('my/', views.client_appointments_view, name='client_appointments'),
    path('<int:appointment_id>/cancel/', views.client_cancel_appointment_view, name='client_cancel'),
    path('schedule/', views.master_schedule_view, name='master_schedule'),
]
