from django.urls import path

from .views import DictionaryLookupView

urlpatterns = [
    path("lookup/<str:word>/", DictionaryLookupView.as_view(), name="dict-lookup"),
]
