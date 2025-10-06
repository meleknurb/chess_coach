from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import ChessGame

class ChessGameAdmin(admin.ModelAdmin):
    list_display = ('user', 'game_date', 'time_control', 'white_player', 'black_player', 'result_description', 'moves_count', 'cached_at')
    list_filter = ('game_date', 'time_control', 'result_description', 'user')
    
    search_fields = ('white_player', 'black_player', 'result_description', 'user__username')
    date_hierarchy = 'game_date'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'pgn'),
        }),
        ('Game Details', {
            'fields': ('game_date', 'time_control', 'result_description', 'moves_count'),
            'classes': ('collapse',),
        }),
        ('Players', {
            'fields': ('white_player', 'black_player'),
        }),
    )

admin.site.register(ChessGame, ChessGameAdmin)