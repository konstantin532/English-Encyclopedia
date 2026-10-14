from django.urls import path

from . import views

app_name = "learning"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("markers/", views.toggle_markers, name="toggle_markers"),
    path("review/", views.review, name="review"),
    path("weeks/<int:week_id>/goal/", views.week_goal, name="week_goal"),
]
