"""URL routing for django-mops-agents.

Merged from agents/urls.py and documents/urls.py.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from mops import api, views

urlpatterns = [
    # Views
    path("", views.index, name="index"),
    path("agents/<str:agent_slug>/", views.agent_detail, name="agent_detail"),
    path("conversations/", views.conversation_list, name="conversation_list"),
    path(
        "conversations/<int:conversation_id>/",
        views.conversation_detail,
        name="conversation_detail",
    ),
    path(
        "conversations/<int:conversation_id>/history/",
        views.conversation_history,
        name="conversation_history",
    ),
    # API
    path("api/", api.api.urls),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
