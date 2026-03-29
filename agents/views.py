from django.shortcuts import get_object_or_404, render

from agents.models import Agent
from agents.services import chat

def index(request):
    agents = Agent.objects.all()
    return render(request, "agents/index.html", {"agents": agents})

def detail(request, agent_slug):
    agent = get_object_or_404(Agent, slug=agent_slug)
    return render(request, "agents/detail.html", {"agent": agent})

def chat(request, agent_slug):
    agent = get_object_or_404(Agent, slug=agent_slug)
    message = None
    if request.method == "POST":
        message = request.POST.get("message")

    response = chat(agent, message) if message else None

    return render(
        request,
        "agents/chat.html",
        {
            "agent": agent,
            "message": message,
            "response": response,
        })