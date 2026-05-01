from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema
from ninja.responses import Response

from agents.models import Agent, Conversation
from agents.services import chat


class MessageIn(Schema):
    message: str


class ConversationOut(Schema):
    id: int
    agent_slug: str
    history: list[dict]


api = NinjaAPI()


@api.post("/agents/{agent_slug}/conversation/")
def create_conversation(request, agent_slug: str):
    agent = get_object_or_404(Agent, slug=agent_slug)
    conversation = Conversation.objects.create(agent=agent, history=[])
    return ConversationOut(
        id=conversation.id,
        agent_slug=conversation.agent.slug,
        history=conversation.history,
    )


@api.post("/agents/{agent_slug}/conversation/{conversation_id}/")
def add_message(request, agent_slug: str, conversation_id: int, data: MessageIn):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    if conversation.agent.slug != agent_slug:
        raise Http404
    chat(conversation, data.message)
    return Response(None, status=204)


@api.get("/agents/{agent_slug}/conversation/{conversation_id}/")
def get_conversation(request, agent_slug: str, conversation_id: int):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    if conversation.agent.slug != agent_slug:
        raise Http404
    return ConversationOut(
        id=conversation.id,
        agent_slug=conversation.agent.slug,
        history=conversation.history,
    )
