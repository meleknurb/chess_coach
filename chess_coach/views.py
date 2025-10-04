from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

# Home view
def home(request):
    return render(request, 'home.html', {'user': request.user})