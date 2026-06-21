"""Dependency resolver for code-defined agents.

This module provides functionality to resolve agent dependencies from
configuration slugs to actual objects (DB models, PydanticAI Tools, etc.).
"""

import inspect
import types
from typing import get_origin, get_args, Any, Union
from pydantic_ai import Tool as PydanticTool, Agent
from mops.models import Prompt, LLMProvider, Collection, AgentConfig, ToolConfig
from mops.registry import get_agent_factory, get_tool_factory


# Custom exceptions
class DependencyNotFoundError(ValueError):
    """Raised when a dependency slug is not found."""
    pass


class InvalidTypeError(ValueError):
    """Raised when a dependency type is invalid or unsupported."""
    pass


def _is_optional_type(param_type: type) -> bool:
    """Check if a type annotation is Optional (Union with None or | None)."""
    origin = get_origin(param_type)
    # Handle Union[T, None] from typing
    if origin is Union:
        return type(None) in get_args(param_type)
    # Handle T | None from Python 3.10+ (types.UnionType)
    if origin is types.UnionType:
        return type(None) in get_args(param_type)
    return False


# Map of dependency types to their resolution strategies
_DB_TYPE_MAP = {
    Prompt: Prompt,
    LLMProvider: LLMProvider,
    Collection: Collection,
    ToolConfig: ToolConfig,
}


def resolve_dependency(param_type: type, slug: str | list[str] | None) -> Any:
    """Resolve a dependency slug (or list of slugs) to the actual object(s).
    
    Handles:
    - PydanticAI Tool types (instantiated from ToolConfig via tool factory)
    - DB model types (Prompt, LLMProvider, Collection, ToolConfig)
    - list[PydanticTool] (multiple ToolConfigs -> multiple PydanticTools)
    - list[DB model] (multiple DB objects via slug__in query)
    - Optional types (e.g., Prompt | None)
    - None values (for Optional parameters)
    
    Args:
        param_type: The expected type of the dependency.
        slug: The slug (or list of slugs) to resolve.
    
    Returns:
        The resolved object(s).
    
    Raises:
        DependencyNotFoundError: If a dependency slug is not found.
        InvalidTypeError: If the dependency type is invalid or unsupported.
    """
    # Handle None (for Optional parameters)
    if slug is None:
        # Check if the type is Optional (Union with None or | None)
        if _is_optional_type(param_type):
            return None
        raise InvalidTypeError(f"Non-optional parameter {param_type} cannot be None")

    # Handle PydanticAI Tool types (resolved from ToolConfig + factory)
    if param_type is PydanticTool:
        # slug must be a ToolConfig slug
        try:
            tool_config = ToolConfig.objects.get(slug=slug)
        except ToolConfig.DoesNotExist:
            raise DependencyNotFoundError(f"ToolConfig with slug '{slug}' not found")
        
        factory = get_tool_factory(tool_config.tool_slug)
        return factory(**tool_config.parameters)

    # Handle list types
    if get_origin(param_type) is list:
        inner_type = get_args(param_type)[0]

        # Handle list[PydanticTool]
        if inner_type is PydanticTool:
            tool_configs = ToolConfig.objects.filter(slug__in=slug)
            tools = []
            for tc in tool_configs:
                factory = get_tool_factory(tc.tool_slug)
                tools.append(factory(**tc.parameters))
            return tools

        # Handle list of DB model types
        inner_model = _DB_TYPE_MAP.get(inner_type)
        if inner_model:
            return list(inner_model.objects.filter(slug__in=slug))

        raise InvalidTypeError(f"Unknown list dependency type: {param_type}")

    # Handle DB model types
    model_class = _DB_TYPE_MAP.get(param_type)
    if model_class:
        try:
            return model_class.objects.get(slug=slug)
        except model_class.DoesNotExist:
            raise DependencyNotFoundError(f"{model_class.__name__} with slug '{slug}' not found")

    raise InvalidTypeError(f"Unknown dependency type: {param_type}")


def get_agent(slug: str) -> Agent:
    """Resolve an agent by its AgentConfig slug, injecting all dependencies.
    
    Steps:
    1. Load AgentConfig from DB
    2. Get factory function from registry
    3. Inspect factory signature
    4. For each parameter, resolve slug(s) to actual objects
    5. Call factory with resolved dependencies
    
    Args:
        slug: The AgentConfig slug.
    
    Returns:
        A pydantic_ai.Agent instance.
    
    Raises:
        AgentConfig.DoesNotExist: If the AgentConfig is not found.
        DependencyNotFoundError: If a required dependency is missing.
        InvalidTypeError: If a dependency type is invalid.
    """
    try:
        config = AgentConfig.objects.get(slug=slug)
    except AgentConfig.DoesNotExist:
        raise DependencyNotFoundError(f"AgentConfig with slug '{slug}' not found")
    
    factory = get_agent_factory(config.implementation)
    sig = inspect.signature(factory)

    kwargs = {}
    for param_name, param in sig.parameters.items():
        if param_name not in config.parameters:
            # Check if parameter has a default value
            if param.default is inspect.Parameter.empty:
                raise DependencyNotFoundError(
                    f"AgentConfig for '{config.slug}' missing parameter '{param_name}' "
                    f"required by implementation '{config.implementation}'"
                )
            # Use default value
            kwargs[param_name] = param.default
            continue

        param_slug = config.parameters[param_name]
        param_type = param.annotation
        kwargs[param_name] = resolve_dependency(param_type, param_slug)

    return factory(**kwargs)


def validate_agent_config(config: AgentConfig) -> list[str]:
    """Validate that an AgentConfig's parameters match its implementation's signature.
    
    Returns list of error messages, empty if valid.
    Supports Optional and list types.
    
    Args:
        config: The AgentConfig to validate.
    
    Returns:
        A list of error messages. Empty if the config is valid.
    """
    errors = []
    try:
        factory = get_agent_factory(config.implementation)
    except KeyError:
        errors.append(f"Implementation '{config.implementation}' not registered")
        return errors

    sig = inspect.signature(factory)
    param_names = set(sig.parameters.keys())
    config_param_names = set(config.parameters.keys())

    # Check for missing required parameters (no default value)
    for param_name, param in sig.parameters.items():
        if param.default is inspect.Parameter.empty and param_name not in config_param_names:
            errors.append(
                f"Missing required parameter '{param_name}' in config for implementation "
                f"'{config.implementation}'"
            )

    # Check for extra parameters in config
    extra = config_param_names - param_names
    for p in extra:
        errors.append(
            f"Extra parameter '{p}' in config not used by implementation "
            f"'{config.implementation}'"
        )

    # Check parameter types (basic validation)
    for param_name, param in sig.parameters.items():
        if param_name in config.parameters:
            param_type = param.annotation
            param_slug = config.parameters[param_name]

            # Skip None checks for Optional types
            if param_slug is None:
                # Check if the type is Optional (Union with None or | None)
                if not _is_optional_type(param_type):
                    errors.append(
                        f"Parameter '{param_name}' is None but type {param_type} is not Optional"
                    )
                continue

            # For list types, validate slug is a list
            if get_origin(param_type) is list:
                if not isinstance(param_slug, list):
                    errors.append(
                        f"Parameter '{param_name}' expects list but got {type(param_slug).__name__}"
                    )

    return errors
