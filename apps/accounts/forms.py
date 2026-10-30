from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class SignupForm(UserCreationForm):
    role = forms.ChoiceField(
        label="Как вы будете пользоваться энциклопедией?",
        choices=(("student", "Ученик"), ("teacher", "Учитель")),
        initial="student", required=False, widget=forms.RadioSelect,
    )

    class Meta:
        model = User
        fields = ("email",)
        labels = {"email": "Почта"}
        widgets = {"email": forms.EmailInput(attrs={"autocomplete": "email"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Выбор роли предшествует почте и не должен пропускаться автофокусом.
        self.fields["email"].widget.attrs.pop("autofocus", None)

    def clean_role(self):
        # Старые клиенты без выбора роли по-прежнему создают ученика.
        return self.cleaned_data.get("role") or "student"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.teacher_access_requested = self.cleaned_data["role"] == "teacher"
        if commit:
            user.save()
        return user

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
