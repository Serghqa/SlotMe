from django.shortcuts import render
from .models import Master


def master_list_view(request):
    masters = Master.objects.filter(is_active=True)
    return render(request, 'masters/master_list.html', {'masters': masters})
