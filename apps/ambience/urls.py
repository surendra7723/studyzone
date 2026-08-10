from django.urls import path

from .views import AmbienceCategoryListView, AmbienceTrackListView

app_name = "ambience"

urlpatterns = [
    path("tracks/", AmbienceTrackListView.as_view(), name="track-list"),
    path("categories/", AmbienceCategoryListView.as_view(), name="category-list"),
]
