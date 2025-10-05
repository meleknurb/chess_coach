from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required 
def analyze_game(request):
    pgn_data = request.GET.get('pgn', '')
    
    context = {
        'pgn': pgn_data,
    }
    return render(request, 'analyze.html', context)