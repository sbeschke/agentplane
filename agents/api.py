from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Schema

from agents.models import Agent
from agents.services import chat


class ConversationIn(Schema):
    message: str


class ConversationOut(Schema):
    response: str


api = NinjaAPI()


@api.post("/agents/{agent_slug}/conversation/")
def start_conversation(request, agent_slug: str, data: ConversationIn):
    agent = get_object_or_404(Agent, slug=agent_slug)
    response = chat(agent, data.message)
    return ConversationOut(response=response)
