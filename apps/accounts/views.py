from urllib.parse import urlsplit

from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render, resolve_url

from .forms import LoginForm, SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("learning:dashboard")
    form = SignupForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("learning:dashboard")
    return render(request, "accounts/signup.html", {"form": form})


class EmailLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_redirect_url(self):
        redirect_to = super().get_redirect_url()
        # LoginView raises ValueError for an authenticated redirect back to itself.
        # Ignore the same login path (including query strings) for guests too.
        if urlsplit(redirect_to).path == self.request.path:
            return ""
        return redirect_to

    def get_default_redirect_url(self):
        # Учитель после входа попадает в свой кабинет, ученик — в курс.
        from apps.teaching.access import can_teach
        if can_teach(self.request.user):
            return resolve_url("teaching:dashboard")
        return super().get_default_redirect_url()
