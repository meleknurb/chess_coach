from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, update_session_auth_hash 
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserUpdateForm, ChessUsernameUpdateForm
from .models import CustomUser, ChesscomPlayer, PlayerRating
from django.contrib.auth.forms import PasswordChangeForm 
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
from django.http import JsonResponse
from django.utils import timezone


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

DEFAULT_LIMIT = 5

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

def get_rating_data(stats_data, time_class_key):
    data = stats_data.get(time_class_key, {})
    
    current_rating = 0
    score_change = 0 
    
    last_data = data.get('last', {})
    current_rating_value = last_data.get('rating')
    
    if isinstance(current_rating_value, (int, float)):
        current_rating = int(current_rating_value)

    prev_rating = last_data.get('prev', 0)
    if current_rating != 0 and prev_rating != 0:
        score_change = current_rating - prev_rating
        
    record = data.get('record', {})
    win, loss, draw = record.get('win', 0), record.get('loss', 0), record.get('draw', 0)
    total = win + loss + draw
    
    return {
        'rating': current_rating,
        'change': score_change,
        'total_games': total,
        'win_count': win, 
        'loss_count': loss,
        'draw_count': draw,
    }

def extract_country_code(country_url):
    if country_url:
        return country_url.split('/')[-1].upper()
    return None 


def update_player_data(user):
    username = user.username.lower()
    
    try:
        # 1. Player Profile Info API Call
        player_info_url = f'https://api.chess.com/pub/player/{username}'
        player_info_response = requests.get(player_info_url, headers=API_HEADERS, timeout=5)
        player_info_response.raise_for_status()
        player_info = player_info_response.json()
        
        # 2. Player Stats API Call
        stats_url = f'https://api.chess.com/pub/player/{username}/stats'
        stats_response = requests.get(stats_url, headers=API_HEADERS, timeout=5)
        stats_response.raise_for_status()
        stats_data = stats_response.json()

    except requests.exceptions.RequestException as e:
        print(f"API Connection Error for {username}: {e}")
        return False 
    
    player_obj, created = ChesscomPlayer.objects.update_or_create(
        user=user, 
        defaults={
            'username': username,
            'country_code': extract_country_code(player_info.get('country')),
            'last_updated': timezone.now()
        }
    )
    
    rating_classes = {
        'bullet': 'chess_bullet',
        'blitz': 'chess_blitz',
        'rapid': 'chess_rapid',
    }
    
    for time_class, api_key in rating_classes.items():
        api_data = get_rating_data(stats_data, api_key)
        new_rating = api_data['rating']
        
        rating_obj, created = PlayerRating.objects.get_or_create(
            player=player_obj,
            time_class=time_class,
            defaults={'rating': new_rating}
        )
        
        if created or rating_obj.rating != new_rating:
            rating_obj.rating = new_rating
            rating_obj.rating_change = api_data['change']
            rating_obj.total_games = api_data['total_games']
            rating_obj.win_count = api_data['win_count']
            rating_obj.loss_count = api_data['loss_count']
            rating_obj.draw_count = api_data['draw_count']
            rating_obj.last_updated = timezone.now()
            rating_obj.save()
            print(f"Rating CHANGE detected for {time_class}. Updated to {new_rating}.")
        else:
            print(f"Rating UNCHANGED for {time_class}. Using local DB data.")

        
    return True

def get_player_context_from_db(user):
    username = user.username.lower()
    
    try:
        player_obj = ChesscomPlayer.objects.get(user=user)
    except ChesscomPlayer.DoesNotExist:
        return None 
    
    ratings_db = player_obj.ratings.all()
    ratings = {}
    
    for rating_obj in ratings_db:
        score_change = rating_obj.rating_change
        
        ratings[rating_obj.time_class] = {
            'rating': str(rating_obj.rating) if rating_obj.rating else 'N/A', 
            'change': score_change,
            'change_text': f"{'+' if score_change >= 0 else ''}{score_change}",
            'change_class': 'up' if score_change > 0 else ('down' if score_change < 0 else 'neutral'),
        }

    app_joined_date_str = user.date_joined.strftime("%d %b %Y") 
    
    context = {
        'username': username,
        'player_info': {
            'joined': app_joined_date_str,
            'followers': 0,  
            'country_code': player_obj.country_code,
        },
        'ratings': ratings,
    }
    return context

@login_required
def profile(request):
    user = request.user
    username = user.username.lower()
    api_success = update_player_data(user) 
    context = get_player_context_from_db(user)
    
    if context is None:
        if not api_success:
             messages.error(request, 'Error: Could not retrieve any player data. Chess.com API may be down, and no previous data was found in the database.')
        else:
             messages.error(request, 'Error: Failed to fetch profile information.')
             
        context = {'username': username, 'player_info': {'joined': 'N/A', 'followers': 0, 'country_code': None}, 'ratings': {}}

        
    context['active_tab'] = 'overview'

    return render(request, 'profile.html', context)

@login_required
def settings(request):
    user = request.user

    email_form = UserUpdateForm(instance=user)
    password_form = PasswordChangeForm(user)
    chess_username_form = ChessUsernameUpdateForm(instance=user)

    if request.method == 'POST':
        
        if 'update_email' in request.POST:
            email_form = UserUpdateForm(request.POST, instance=user)
            if email_form.is_valid():
                email_form.save()
                messages.success(request, "Email address successfully updated.")
                return redirect('users:settings')

        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password was successfully updated!")
                return redirect('users:settings')
        

        elif 'update_chess_username' in request.POST:
            chess_username_form = ChessUsernameUpdateForm(request.POST, instance=user)
            
            if chess_username_form.is_valid():
                new_username = chess_username_form.cleaned_data.get('username')
                
                if new_username is not None:
                    chess_username_form.save() 
                    ChessGame.objects.filter(user=request.user).delete()
                    messages.success(request, f"Chess.com username successfully set to '{new_username}'.")
                else:
                    messages.error(request, "Username cannot be empty.")
                
                return redirect('users:settings')
            
            messages.error(request, "Error: Please check the entered username.")
            return redirect('users:settings')


    context = {
        'email_form': email_form,
        'password_form': password_form,
        'chess_username_form': chess_username_form,
    }
    return render(request, 'settings.html', context)

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
 
        auth_logout(request)
        
        try:
            user.delete()
            return redirect('home') 
            
        except Exception as e:
            print(f"Error deleting user {user.username}: {e}")
            messages.error(None, 'An error occurred while trying to delete the account. Please try again.')
            return redirect('home') 
                    
    return redirect('users:settings')

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

@login_required
def search_games(request):
    query = request.GET.get('query', '').strip().lower()
    username = request.user.username.lower()
    results = []
    
    db_games_qs = ChessGame.objects.filter(user=request.user)
    
    if query:
        filtered_db_games_qs = db_games_qs.filter(
            white_player__icontains=query
        ) | db_games_qs.filter(
            black_player__icontains=query
        ) | db_games_qs.filter(
            game_date__icontains=query
        )
        
        for game in filtered_db_games_qs.order_by('-game_date', '-cached_at'):
            results.append({
                'pk': game.pk,
                'player_top': game.white_player,
                'player_bottom': game.black_player,
                'time_control': game.time_control,
                'result_description': game.result_description,
                'moves_count': game.moves_count,
                'date': game.game_date.strftime("%b %d, %Y"),
            })

    if not results and query:
        print(f"Searching from API: {query}")
        new_games_saved = 0
        try:
            archives_url = f'https://api.chess.com/pub/player/{username}/games/archives'
            archives_response = requests.get(archives_url, headers=API_HEADERS, timeout=10)
            archives_response.raise_for_status()
            archives = archives_response.json().get('archives', [])

            recent_archives = archives[-6:]

            for archive_url in reversed(recent_archives):
                games_response = requests.get(archive_url, headers=API_HEADERS, timeout=10)
                games_response.raise_for_status()
                api_games = games_response.json().get('games', [])

                for g in api_games:
                    pgn_text = g.get('pgn', '')
                    opponent = g['black']['username'] if g['white']['username'].lower() == username else g['white']['username']
                    
                    game_date_db = datetime.datetime.fromtimestamp(g['end_time'], tz=datetime.timezone.utc).date()

                    if query in opponent.lower() or query in game_date_db.strftime('%Y-%m-%d'):
                        
                        if ChessGame.objects.filter(user=request.user, pgn=pgn_text).exists():
                            existing_game = ChessGame.objects.get(user=request.user, pgn=pgn_text)
                            pk_value = existing_game.pk
                        else:
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

                            moves_count = get_moves_from_pgn(pgn_text)

                            new_game_obj = ChessGame.objects.create(
                                user=request.user, pgn=pgn_text, game_date=game_date_db,
                                white_player=white_player_formatted, black_player=black_player_formatted,
                                time_control=g.get('time_class', 'Unknown').capitalize(),
                                result_description=display_result, moves_count=moves_count,
                            )
                            new_games_saved += 1
                            pk_value = new_game_obj.pk

                        results.append({
                            'pk': pk_value,
                            'player_top': white_player_formatted, 
                            'player_bottom': black_player_formatted,
                            'time_control': new_game_obj.time_control if 'new_game_obj' in locals() else existing_game.time_control,
                            'result_description': new_game_obj.result_description if 'new_game_obj' in locals() else existing_game.result_description,
                            'moves_count': moves_count,
                            'date': game_date_db.strftime("%b %d, %Y"),
                        })

                        if len(results) >= 10:
                            break
                
                if len(results) >= 10:
                    break
            
            if new_games_saved > 0:
                 print(f"{new_games_saved} number of games matching the search criteria were saved in the DB.")

        except requests.RequestException as e:
            print("API search failed:", e)

    return JsonResponse({'games': results})

@login_required
def load_more_games(request):

    offset = int(request.GET.get('offset', DEFAULT_LIMIT))
    limit = DEFAULT_LIMIT
    username = request.user.username.lower()
    
    db_games_qs = ChessGame.objects.filter(user=request.user).order_by('-game_date', '-cached_at')
    games_to_return = db_games_qs[offset:offset + limit]
    
    games_list = []
    
    if games_to_return.exists():
        print(f"Loading {games_to_return.count()} games from DB cache (offset: {offset}).")
        for game_obj in games_to_return:
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
        
        has_more_db_games = db_games_qs.count() > (offset + limit)

        return JsonResponse({
            'games': games_list,
            'loaded_from': 'db',
            'has_more_db_games': has_more_db_games
        })

    print("DB cache is exhausted. Attempting to sync/load from API.")
    
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
            
            new_games_saved_count = 0
            
            for g in reversed(api_games):
                pgn_text = g.get('pgn', '')
                
                if not ChessGame.objects.filter(user=request.user, pgn=pgn_text).exists():
                    game_datetime = datetime.datetime.fromtimestamp(g['end_time'], tz=datetime.timezone.utc)
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

                    moves_count = get_moves_from_pgn(pgn_text)
                    new_game_obj = ChessGame.objects.create(
                        user=request.user, pgn=pgn_text, game_date=game_date_db,
                        white_player=white_player_formatted, black_player=black_player_formatted,
                        time_control=g.get('time_class', 'Unknown').capitalize(),
                        result_description=display_result, moves_count=moves_count,
                    )
                    
                    games_list.append({
                        'pk': new_game_obj.pk,
                        'player_top': white_player_formatted,
                        'player_bottom': black_player_formatted,
                        'time_control': new_game_obj.time_control,
                        'result_description': new_game_obj.result_description,
                        'moves_count': new_game_obj.moves_count,
                        'date': new_game_obj.game_date.strftime("%b %d, %Y"),
                        'is_user_white': is_user_white,
                    })
                    
                    new_games_saved_count += 1

                    if new_games_saved_count >= limit:
                        break
                        
            if new_games_saved_count > 0:
                return JsonResponse({
                    'games': games_list,
                    'loaded_from': 'api',
                    'has_more_db_games': True 
                })

    except requests.exceptions.RequestException as e:
        print(f"ERROR: API connection failed during Load More: {e}")
        pass 
    except Exception as e:
        print(f"Error during API sync or processing in Load More: {e}")
        pass

    return JsonResponse({
        'games': [],
        'loaded_from': 'none',
        'has_more_db_games': False
    })
