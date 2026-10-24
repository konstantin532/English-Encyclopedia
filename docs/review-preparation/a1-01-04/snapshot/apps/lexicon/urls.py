from django.urls import path

from . import views

app_name = "lexicon"
urlpatterns = [
    path("", views.unit_list, name="list"),
    path("<str:uid>/", views.unit_detail, name="detail"),
]
