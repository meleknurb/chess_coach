from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# Create your models here.

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password):
        if not username:
            raise ValueError('The Chess.com username field must be set')
        if not email:
            raise ValueError('The Email field must be set')
        if not password:
            raise ValueError('The Password field must be set')

        email = self.normalize_email(email)
        user = self.model(username=username, email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password):
        user = self.create_user(username=username, email=email, password=password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class CustomUser(AbstractUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username


class ChesscomPlayer(models.Model):
    user = models.OneToOneField( 
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='chess_profile',
        verbose_name='App User'
    )
    username = models.CharField(
        max_length=150, 
        unique=True, 
        db_index=True,
        verbose_name='Chess.com Username'
    )
    country_code = models.CharField(
        max_length=2, 
        null=True, 
        blank=True,
        verbose_name='Country Code'
    )
    joined_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Joined Date'
    )
    followers = models.IntegerField(
        default=0, 
        verbose_name='Followers'
    )
    last_updated = models.DateTimeField(
        default=timezone.now,
        verbose_name='Last Updated'
    )

    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name = 'Chess.com Player'
        verbose_name_plural = 'Chess.com Players'
        

class PlayerRating(models.Model):
    TIME_CLASS_CHOICES = (
        ('bullet', 'Bullet'),
        ('blitz', 'Blitz'),
        ('rapid', 'Rapid'),
    )
    
    player = models.ForeignKey(
        ChesscomPlayer,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    time_class = models.CharField(
        max_length=10,
        choices=TIME_CLASS_CHOICES,
        db_index=True,
        verbose_name='Time Class'
    )
    rating = models.IntegerField(
        default=0,
        verbose_name='Rating'
    )
    rating_change = models.IntegerField(
        default=0,
        verbose_name='Rating Change'
    )
    total_games = models.IntegerField(default=0)
    win_count = models.IntegerField(default=0)
    loss_count = models.IntegerField(default=0)
    draw_count = models.IntegerField(default=0)
    
    last_updated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.player.username} - {self.time_class}: {self.rating}"

    class Meta:
        unique_together = ('player', 'time_class')
        verbose_name = 'Player Rating'
        verbose_name_plural = 'Player Ratings'
