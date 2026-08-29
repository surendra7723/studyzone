from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import DictionaryLookupView, SearchHistoryViewSet, WordEntryViewSet

app_name = "dictionary"

router = DefaultRouter()
router.register(r'history', SearchHistoryViewSet, basename='search-history')
router.register(r'words', WordEntryViewSet, basename='word-entry')

urlpatterns = [
    path('lookup/<str:word>/', DictionaryLookupView.as_view(), name='dict-lookup'),
    path('', include(router.urls)),
]
