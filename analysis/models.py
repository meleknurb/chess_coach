from django.db import models
from django.conf import settings 


# Create your models here.
class ChessGame(models.Model):
    # Foreign Key linking the game to the user who fetched it
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cached_games',
        verbose_name='User'
    )
    
    # The full PGN data
    pgn = models.TextField(
        verbose_name='PGN Data'
    )
    
    # Essential game details for dashboard display
    game_date = models.DateField(
        verbose_name='Game Date'
    )
    white_player = models.CharField(
        max_length=200,
        verbose_name='White Player'
    )
    black_player = models.CharField(
        max_length= 200,
        verbose_name='Black Player'
    )
    time_control = models.CharField(
        max_length=50,
        verbose_name='Time Control'
    )
    result_description = models.CharField(
        max_length=50,
        verbose_name='Result'
    )
    moves_count = models.IntegerField(
        default=0,
        verbose_name='Move Count'
    )
    
    # Timestamp for caching (used for sorting and potential future cache logic)
    cached_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Cached At'
    )

    class Meta:
        verbose_name = "Chess Game"
        verbose_name_plural = "Chess Games"
        # Ensures a user doesn't save the same PGN multiple times
        unique_together = ('user', 'pgn') 
        # Default sorting: Newest games first
        ordering = ['-game_date', '-cached_at']

    def __str__(self):
        return f"{self.user.username}: {self.white_player} vs {self.black_player} ({self.game_date})"