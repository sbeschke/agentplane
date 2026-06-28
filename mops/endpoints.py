"""Agent endpoints for code-defined agents.

This module provides REST API endpoints for code-defined agents.
"""

from ninja import Router
from mops.resolver import get_agent, DependencyNotFoundError, InvalidTypeError
from mops.models import AgentConfig


def create_agent_router(slug: str) -> Router:
    """Create a router for a specific agent.

    Args:
        slug: The AgentConfig slug for the agent.

    Returns:
        A NinjaAPI Router with endpoints for the agent.
    """
    router = Router()

    @router.post("/")
    def run_agent(request, message: str):
        """Run the agent with a message.

        Args:
            request: The HTTP request.
            message: The user's message to the agent.

        Returns:
            A JSON response containing the agent's reply.

        Raises:
            HTTP_404: If the agent config is not found.
            HTTP_400: If there's a dependency resolution error.
        """
        try:
            agent = get_agent(slug)
            result = agent.run(message)
            return {"response": str(result)}
        except DependencyNotFoundError as e:
            return {"error": str(e)}, 404
        except InvalidTypeError as e:
            return {"error": str(e)}, 400
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}, 500

    @router.get("/")
    def get_agent_info(request):
        """Get agent configuration info.

        Args:
            request: The HTTP request.

        Returns:
            A JSON response with agent configuration details.

        Raises:
            HTTP_404: If the agent config is not found.
        """
        try:
            config = AgentConfig.objects.get(slug=slug)
            return {
                "slug": config.slug,
                "name": config.name,
                "description": config.description,
                "implementation": config.implementation,
            }
        except AgentConfig.DoesNotExist:
            return {"error": f"AgentConfig with slug '{slug}' not found"}, 404

    return router
