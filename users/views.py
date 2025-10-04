from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login as auth_login 
from django.contrib.auth import logout as auth_logout

# Create your views here.

# Registration view
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

# Login view
def login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user:
                auth_login(request, user)
                return redirect('users:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'login.html', {'form': form})

# Logout view
@login_required
def logout(request):
    auth_logout(request)
    return redirect('home')

@login_required
def profile(request):
    return render(request, 'profile.html', {'user': request.user})

@login_required
def settings(request):
    return render(request, 'settings.html', {'user': request.user})

@login_required
def dashboard(request):
    context = {
        'username': request.user.username,
        'user_rating': 1850,
    }
    return render(request, 'dashboard.html', context)
