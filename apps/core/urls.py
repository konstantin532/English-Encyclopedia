from django.urls import path

from . import a1_active, cafe_lab, classics, observability, public_metadata, views

app_name = "core"
urlpatterns = [
    path("robots.txt", public_metadata.robots, name="robots"),
    path("sitemap.xml", public_metadata.sitemap, name="sitemap"),
    path("", views.home, name="home"),
    path("classics/", classics.classics_page, name="classics"),
    path("healthz/", views.healthz, name="healthz"),
    path("metrics/", observability.metrics_view, name="metrics"),
    path("lab/cafe/", cafe_lab.cafe_lab, name="cafe_lab"),
    path("lab/a1/<int:number>/", a1_active.active_a1_topic, name="active_a1_topic"),
]
