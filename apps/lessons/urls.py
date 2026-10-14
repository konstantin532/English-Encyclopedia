from django.urls import path

from . import views

app_name = "lessons"
urlpatterns = [path("<slug:slug>/", views.lesson_detail, name="detail")]
