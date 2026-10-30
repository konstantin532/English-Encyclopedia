from urllib.parse import urlsplit

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render, resolve_url
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, SignupForm


def account_landing(user):
    from apps.teaching.access import can_teach

    if can_teach(user):
        return "teaching:dashboard"
    if user.teacher_access_requested:
        return "accounts:teacher_request"
    return "learning:dashboard"


def safe_next(request):
    """Same-origin destinations only, excluding authentication redirect loops."""
    destination = request.POST.get("next", request.GET.get("next", ""))
    if not url_has_allowed_host_and_scheme(
        destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return ""
    if urlsplit(destination).path in {reverse("accounts:login"), reverse("accounts:signup")}:
        return ""
    return destination


def signup(request):
    if request.user.is_authenticated:
        return redirect(account_landing(request.user))
    next_url = safe_next(request)
    form = SignupForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        # Учителю сначала показываем, что заявка ещё не одобрена.
        return redirect(account_landing(user) if user.teacher_access_requested else next_url or account_landing(user))
    return render(request, "accounts/signup.html", {"form": form, "next": next_url})


@login_required
def teacher_request(request):
    if account_landing(request.user) != "accounts:teacher_request":
        return redirect(account_landing(request.user))
    return render(request, "accounts/teacher_request.html", {"auth_entry": True})


class EmailLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_redirect_url(self):
        return safe_next(self.request)

    def get_default_redirect_url(self):
        return resolve_url(account_landing(self.request.user))
