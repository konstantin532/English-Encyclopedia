from django.urls import path

from . import a1_active, cafe_lab, views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("lab/cafe/", cafe_lab.cafe_lab, name="cafe_lab"),
    path("lab/a1/<int:number>/", a1_active.active_a1_topic, name="active_a1_topic"),
]
