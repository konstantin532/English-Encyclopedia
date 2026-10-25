from django.urls import path

from . import views

app_name = "taxonomy"
urlpatterns = [path("", views.legend, name="legend")]
