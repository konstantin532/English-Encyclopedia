from django.urls import path

from . import views

app_name = "teaching"
urlpatterns = [
    path("for-teachers/", views.for_teachers, name="for_teachers"),
    path("teacher/", views.dashboard, name="dashboard"),
    path("teacher/students/", views.students, name="students"),
    path("teacher/students/<int:pk>/", views.student_detail, name="student"),
    path("teacher/review/", views.review_list, name="review_list"),
    path("teacher/review/<int:pk>/", views.review_detail, name="review"),
    path("teacher/drafts/", views.draft_list, name="drafts"),
    path("teacher/drafts/new/", views.draft_edit, name="draft_new"),
    path("teacher/drafts/<int:pk>/", views.draft_edit, name="draft_edit"),
    path("teacher/drafts/<int:pk>/delete/", views.draft_delete, name="draft_delete"),
    path("report-issue/", views.report_issue, name="report_issue"),
    path("group/", views.join_group, name="join"),
    path("group/leave/", views.leave_group, name="leave"),
]
