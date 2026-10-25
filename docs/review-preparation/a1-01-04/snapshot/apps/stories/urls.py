from django.urls import path

from . import views

app_name = "stories"
urlpatterns = [
    path("", views.course_map, name="map"),
    path("<int:number>/", views.story_detail, name="detail"),
    path("poems/<int:number>/", views.poem_detail, name="poem"),
]
