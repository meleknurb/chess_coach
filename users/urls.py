from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('dashboard/', views.dashboard, name='dashboard'), 
    path('search_games/', views.search_games, name='search_games'),
    path('load_more_games/', views.load_more_games, name='load_more_games'),
    path('delete_account/', views.delete_account, name='delete_account'),

]