from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('book/<int:master_id>/', views.book_appointment_view, name='book'),
    path('my/', views.client_appointments_view, name='client_list'),
    path('<int:appointment_id>/cancel/', views.cancel_appointment_view, name='cancel'),
]
