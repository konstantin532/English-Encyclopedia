from django.urls import path

from . import views, speech_practice, delayed_review_views, independent_views

app_name = "learning"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("markers/", views.toggle_markers, name="toggle_markers"),
    path("review/", views.review, name="review"),
    path("speech-practice/", speech_practice.speech_practice_api, name="speech_practice"),
    path("speech-review/", speech_practice.speech_review, name="speech_review"),
    path("mistake-review/", delayed_review_views.mistake_review, name="mistake_review"),
    path("independent/<slug:slug>/", independent_views.independent_check, name="independent_check"),
    path("mistake-review/request/<int:exercise_id>/", delayed_review_views.request_optional_review, name="request_optional_review"),
    path("weeks/<int:week_id>/goal/", views.week_goal, name="week_goal"),
]
