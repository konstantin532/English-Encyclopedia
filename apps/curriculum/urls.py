from django.urls import path

from . import views

app_name = "curriculum"
urlpatterns = [
    path("<slug:slug>/", views.level_detail, name="level"),
    path("<slug:slug>/weeks/<int:number>/", views.week_detail, name="week"),
]
