from django.urls import path

from . import assignment_views, views

app_name = "teaching"
urlpatterns = [
    path("for-teachers/", views.for_teachers, name="for_teachers"),
    path("teacher/", views.dashboard, name="dashboard"),
    path("teacher/assignments/", assignment_views.assignment_list, name="assignments"),
    path("teacher/assignments/new/", assignment_views.assignment_new, name="assignment_new"),
    path("teacher/assignments/overdue/", assignment_views.overdue_list, name="overdue_assignments"),
    path("teacher/assignments/<int:pk>/", assignment_views.assignment_detail, name="assignment"),
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
    path("assignments/<int:pk>/open/", assignment_views.assignment_open, name="assignment_open"),
    path("assignments/<int:pk>/complete/", assignment_views.assignment_complete, name="assignment_complete"),
    path("assignments/<int:pk>/history/", assignment_views.assignment_history, name="assignment_history"),
]
