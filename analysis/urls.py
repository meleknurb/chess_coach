from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('analyze_game/', views.analyze_game, name='analyze_game'), 
]