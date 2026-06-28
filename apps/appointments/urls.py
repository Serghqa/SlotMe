from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('book/<int:master_id>/', views.book_appointment_view, name='book'),
]
