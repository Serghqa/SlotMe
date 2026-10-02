from django.shortcuts import render

def home_view(request):
    """
    Главная страница сайта.
    """
    return render(request, 'core/home.html')
