from django.urls import path
from . import views


app_name = 'masters'


urlpatterns = [
    path('', views.master_list_view, name='master_list')
]
