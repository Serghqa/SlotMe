from django.shortcuts import render, get_object_or_404
from .models import Master


def master_list_view(request):
    masters = Master.objects.filter(is_active=True)
    return render(request, 'masters/master_list.html', {'masters': masters})


def master_detail_view(request, master_id):
    master = get_object_or_404(
        Master.objects.prefetch_related('services'),
        id=master_id,
        is_active=True
    )
    return render(request, 'masters/master_detail.html', {'master': master})
