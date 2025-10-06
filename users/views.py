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
from analysis.models import ChessGame

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

    DEFAULT_LIMIT = 5
    current_limit = DEFAULT_LIMIT 

    latest_db_game = ChessGame.objects.filter(user=request.user).order_by('-game_date', '-cached_at').first()


    try:
        archives_url = f'https://api.chess.com/pub/player/{username}/games/archives'
        archives_response = requests.get(archives_url, headers=API_HEADERS, timeout=10)
        archives_response.raise_for_status()
        archives = archives_response.json().get('archives', [])

        if archives:
            latest_archive_url = archives[-1]

            games_response = requests.get(latest_archive_url, headers=API_HEADERS, timeout=10)
            games_response.raise_for_status()
            api_games = games_response.json().get('games', [])
            latest_api_pgn = api_games[-1].get('pgn', '')
            
            is_new_game = latest_db_game and latest_db_game.pgn != latest_api_pgn
            is_initial_load = not latest_db_game
            
            db_game_count = ChessGame.objects.filter(user=request.user).count()
            is_under_limit = db_game_count < DEFAULT_LIMIT
            
            
            if is_new_game or is_initial_load or is_under_limit:
                
                new_games_to_save = []
                api_games_to_check = api_games[-DEFAULT_LIMIT:]

                for g in api_games_to_check:
                    pgn_text = g.get('pgn', '')
                    
                    if not ChessGame.objects.filter(user=request.user, pgn=pgn_text).exists():
                        new_games_to_save.append(g)

                if new_games_to_save:
                    print(f"Loading {len(new_games_to_save)} new games from API.")
                    
                    for g in new_games_to_save:
                        pgn_text = g.get('pgn', '')
                        moves_count = get_moves_from_pgn(pgn_text)
                        timestamp_sec = g['end_time']
                        game_datetime = datetime.datetime.fromtimestamp(timestamp_sec, tz=datetime.timezone.utc)
                        game_date_db = game_datetime.date()
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

                        ChessGame.objects.create(
                            user=request.user, pgn=pgn_text, game_date=game_date_db,
                            white_player=white_player_formatted, black_player=black_player_formatted,
                            time_control=g.get('time_class', 'Unknown').capitalize(),
                            result_description=display_result, moves_count=moves_count,
                        )
                
            else:
                print("No new games detected. Using local DB cache.")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: API connection failed. Using local DB cache: {e}")
    except Exception as e:
        print(f"Error during API sync or processing: {e}")



    all_games_qs = ChessGame.objects.filter(user=request.user).order_by('-game_date', '-cached_at')
    total_games_count = all_games_qs.count()
    
    games_for_display = all_games_qs[:DEFAULT_LIMIT]
    
    games_list = []
    for game_obj in games_for_display:
        game_info = {
            'pk': game_obj.pk,
            'player_top': game_obj.white_player,
            'player_bottom': game_obj.black_player,
            'time_control': game_obj.time_control,
            'result_description': game_obj.result_description,
            'moves_count': game_obj.moves_count,
            'date': game_obj.game_date.strftime("%b %d, %Y"),
            'is_user_white': game_obj.white_player.lower().startswith(username),
        }
        games_list.append(game_info)

    context = {
        'games': games_list,
        'current_username': username,
        'total_games': total_games_count,
    }
    return render(request, 'dashboard.html', context)

