from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from agents import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<str:agent_slug>/", views.detail, name="detail"),
    path("<str:agent_slug>/chat/", views.chat, name="chat"),
]  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)