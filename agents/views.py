from any_llm import AnyLLM
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
    if request.method == "POST":
        message = request.POST.get("message")

    llm = AnyLLM.create("mistral")
    model = "mistral-small-latest"
    completion = llm.completion(
        model=model,
        messages=[
            {"role": "user", "content": message},
        ],
    )

    return render(
        request,
        "agents/chat.html",
        {
            "agent": agent,
            "message": message,
            "response": completion.choices[0].message.content,
        })