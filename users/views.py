from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login as auth_login 
from django.contrib.auth import logout as auth_logout
import requests
import io 
import chess.pgn # type: ignore
import datetime
from requests.exceptions import RequestException
import locale

# Create your views here.

API_HEADERS = {
    'User-Agent': 'ChessCoach(but still under development)/1.0 (contact: meleknurbacakli5@gmail.com)' 
}

try:
    locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'en_US')
    except locale.Error:
        pass

# Registration view
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('users:dashboard')
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

def get_moves_from_pgn(pgn_text):
    try:
        pgn_io = io.StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        
        if game is None:
            return 0
        moves_count = len(list(game.mainline_moves()))
        
        return (moves_count + 1) // 2
        
    except Exception as e:
        print(f"PGN okuma hatası: {e}")
        return 0

@login_required
def dashboard(request):
    username = request.user.username.lower()

    if 'cached_games' in request.session:
        print("API request skipped: Using cache (Session).")
        games_list = request.session['cached_games']
        
    else:
        games_list = []
        print("Retrieving new data from the API...")

        try:
            # API Requests (Archives ve Games)
            archives_url = f'https://api.chess.com/pub/player/{username}/games/archives'
            archives_response = requests.get(archives_url, headers=API_HEADERS, timeout=10)
            archives_response.raise_for_status() 
            archives = archives_response.json().get('archives', [])
            
            if not archives:
                context = {'games': [], 'current_username': username}
                return render(request, 'dashboard.html', context)

            latest_games_url = archives[-1]
            games_response = requests.get(latest_games_url, headers=API_HEADERS, timeout=10)
            games_response.raise_for_status()
            games = games_response.json().get('games', [])

            temp_games_list = []
            for g in games[-5:]: 
                pgn_text = g.get('pgn', '')
                moves_count = get_moves_from_pgn(pgn_text) 
                
                date_formatted = "N/A"
                try:
                    timestamp_sec = g['end_time'] 
                    game_datetime = datetime.datetime.fromtimestamp(timestamp_sec, tz=datetime.timezone.utc)
                    date_formatted = game_datetime.strftime("%b %d, %Y")
                except Exception:
                    date_formatted = "Tarih Bulunamadı" 

                white_player_formatted = f"{g['white']['username']} ({g['white']['rating']})"
                black_player_formatted = f"{g['black']['username']} ({g['black']['rating']})"

                is_user_white = g['white']['username'].lower() == username
                user_result = g['white']['result'] if is_user_white else g['black']['result']

                if user_result == 'win':
                    display_result = 'Win'
                elif user_result in ['agreed', 'repetition', 'stalemate', 'insufficient', '50move', 'timevsinsufficient', 'draw']:
                    display_result = 'Draw'
                else:
                    display_result = 'Loss'
                
                game_info = {
                    'player_top': white_player_formatted,  
                    'player_bottom': black_player_formatted,
                    'time_control': g.get('time_class', 'Unknown').capitalize(),
                    'result_description': display_result,
                    'is_user_white': is_user_white,
                    'moves_count': moves_count,
                    'pgn': pgn_text,
                    'date': date_formatted, 
                }

                temp_games_list.append(game_info)

            games_list = temp_games_list
            games_list.reverse()
            
            request.session['cached_games'] = games_list
                  
        except RequestException as e:
            print(f"ERROR: Error while retrieving data from API: {e}")
            games_list = []
        except Exception as e:
            print(f"Error: General Error: {e}")
            games_list = []

    context = {
        'games': games_list,
        'current_username': username
    }
    return render(request, 'dashboard.html', context)