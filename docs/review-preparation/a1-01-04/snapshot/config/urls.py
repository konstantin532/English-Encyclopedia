from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "English Encyclopedia Studio"
admin.site.site_title = "English Encyclopedia Studio"
admin.site.index_title = "Редакторская студия"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("markers/", include("apps.taxonomy.urls")),
    path("words/", include("apps.lexicon.urls")),
    path("levels/", include("apps.curriculum.urls")),
    path("lessons/", include("apps.lessons.urls")),
    path("stories/", include("apps.stories.urls")),
    path("learning/", include("apps.learning.urls")),
    path("api/", include("apps.api.urls")),
]
