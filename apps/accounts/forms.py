from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "display_name")
        labels = {"email": "Почта", "display_name": "Как к вам обращаться"}

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Аккаунт с этой почтой уже есть. Войдите или используйте другую почту.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.EmailField(max_length=254, label="Почта", widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}))

    def clean_username(self):
        username = self.cleaned_data["username"].strip().lower()
        # Unicode lowercasing can expand a domain after the first length check.
        self.fields["username"].run_validators(username)
        return username
