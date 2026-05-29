"""URL routing for documents API."""

from django.urls import path

from documents import api

urlpatterns = [
    path("api/", api.api.urls),
]
