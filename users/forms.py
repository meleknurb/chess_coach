from django import forms
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from .models import CustomUser

class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password = make_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class CustomAuthenticationForm(forms.Form):
    username = forms.CharField(label='Username', max_length=150)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

User = get_user_model() 

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label='Email Address', required=True)
    
    class Meta:
        model = User
        fields = ('email',) 

class ChessUsernameUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username',)