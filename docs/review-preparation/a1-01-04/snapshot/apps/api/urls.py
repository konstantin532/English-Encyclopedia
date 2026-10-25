from django.urls import path

from . import views

app_name = "api"
urlpatterns = [
    path("exercises/<int:pk>/check/", views.check_exercise, name="check_exercise"),
    path("practice/<int:pk>/check/", views.check_practice, name="check_practice"),
    path("units/<str:uid>/recall/", views.recall_unit, name="recall_unit"),
    path("poems/<int:number>/gaps/<int:index>/", views.check_poem_gap, name="check_poem_gap"),
]
