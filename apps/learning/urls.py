from django.urls import path

from . import trainer_views, views, speech_practice, delayed_review_views, independent_views, transfer_pilot, cafe_mission

app_name = "learning"
urlpatterns = [
    path("vocabulary/", trainer_views.trainer, name="trainer"),
    path("vocabulary/<int:session_id>/", trainer_views.encounter, name="trainer_session"),
    path("vocabulary/<int:session_id>/status/", trainer_views.status, name="trainer_status"),
    path("", views.dashboard, name="dashboard"),
    path("markers/", views.toggle_markers, name="toggle_markers"),
    path("review/", views.review, name="review"),
    path("speech-practice/", speech_practice.speech_practice_api, name="speech_practice"),
    path("speech-review/", speech_practice.speech_review, name="speech_review"),
    path("mistake-review/", delayed_review_views.mistake_review, name="mistake_review"),
    path("independent/<slug:slug>/", independent_views.independent_check, name="independent_check"),
    path("transfer-pilot/<slug:slug>/", transfer_pilot.transfer_pilot, name="transfer_pilot"),
    path("cafe-mission/", cafe_mission.cafe_mission, name="cafe_mission"),
    path("mistake-review/request/<int:exercise_id>/", delayed_review_views.request_optional_review, name="request_optional_review"),
    path("practice-review/<int:item_id>/", delayed_review_views.request_practice_review, name="request_practice_review"),
    path("weeks/<int:week_id>/goal/", views.week_goal, name="week_goal"),
]
