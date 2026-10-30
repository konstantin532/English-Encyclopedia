from django.contrib.auth.views import LogoutView
from django.urls import path

from . import data_rights, views

app_name = "accounts"
urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("teacher-request/", views.teacher_request, name="teacher_request"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("my-data/", data_rights.download_my_data, name="my_data"),
    path("delete/", data_rights.delete_account, name="delete_account"),
]
