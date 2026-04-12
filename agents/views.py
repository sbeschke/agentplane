from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from agents import services
from agents.models import Agent, Conversation


def index(request):
    agents = Agent.objects.all()
    return render(request, "agents/index.html", {"agents": agents})


def agent_detail(request, agent_slug):
    agent = get_object_or_404(Agent, slug=agent_slug)
    return render(request, "agents/agent_detail.html", {"agent": agent})


def conversation_list(request):
    if request.method == "POST":
        agent_slug = request.POST.get("agent_slug")
        print(f"Creating conversation for agent slug: {agent_slug}")
        agent = get_object_or_404(Agent, slug=agent_slug)
        conversation = agent.conversations.create()
        return redirect("conversation_detail", conversation_id=conversation.id)
    return HttpResponseBadRequest("Invalid method")


def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    if request.method == "POST":
        message = request.POST.get("message")
        if message:
            services.run_agent_chat_task.enqueue(conversation.id, message)
            return render(
                request,
                "agents/partials/conversation_history.html",
                {"conversation": conversation},
            )
    return render(
        request, "agents/conversation_detail.html", {"conversation": conversation}
    )


def conversation_history(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    return render(
        request,
        "agents/partials/conversation_history.html",
        {"conversation": conversation},
    )
