from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import RegistrationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('users:profile')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='apps.users.backend.EmailAuthBackend')
            messages.success(request, f'Регистрация прошла успешно! Добро пожаловать, {user.first_name}!')
            return redirect('users:profile')
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile_view(request):
    return render(request, 'users/profile.html')
