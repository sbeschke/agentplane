from pydantic_ai import Agent as PydanticAgent
from django.shortcuts import get_object_or_404, render

from agents.models import Agent

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

    pydantic_agent = PydanticAgent(
        "mistral:mistral-small-latest",
        instructions=agent.instructions,
    )
    result = pydantic_agent.run_sync(message)

    return render(
        request,
        "agents/chat.html",
        {
            "agent": agent,
            "message": message,
            "response": result.output,
        })