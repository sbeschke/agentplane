from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from agents import api, views

urlpatterns = [
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
    path("api/", api.api.urls),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
