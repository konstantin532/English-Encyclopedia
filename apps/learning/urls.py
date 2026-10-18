from django.urls import path

from . import views, speech_practice

app_name = "learning"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("markers/", views.toggle_markers, name="toggle_markers"),
    path("review/", views.review, name="review"),
    path("speech-practice/", speech_practice.speech_practice_api, name="speech_practice"),
    path("speech-review/", speech_practice.speech_review, name="speech_review"),
    path("weeks/<int:week_id>/goal/", views.week_goal, name="week_goal"),
]
