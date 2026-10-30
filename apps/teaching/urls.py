from django.urls import path

from . import views

app_name = "teaching"
urlpatterns = [
    path("for-teachers/", views.for_teachers, name="for_teachers"),
    path("teacher/", views.dashboard, name="dashboard"),
    path("teacher/students/", views.students, name="students"),
    path("teacher/students/<int:pk>/", views.student_detail, name="student"),
    path("group/", views.join_group, name="join"),
    path("group/leave/", views.leave_group, name="leave"),
]
