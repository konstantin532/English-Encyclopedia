from django.urls import path

from . import cafe_lab, views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("lab/cafe/", cafe_lab.cafe_lab, name="cafe_lab"),
]
