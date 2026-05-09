# Agent Plane - Project Scope

## Overview
Agent Plane is an application for creating and running AI agents. Users can create agents by specifying a system prompt and set of tools that the agent has access to. The platform provides a REST API through which each agent can be called with a prompt.

**Local-first development** is a core part of the vision: agents should run smoothly against local models with minimal setup, alongside optional cloud or third-party providers.

## Core Capabilities
- **REST API for agents**: Programmatic access to agent functionality
- **LLM provider configuration**: Support for both local LLM execution and third-party providers via API keys
- **Built-in RAG capability**: The app allows users to create document collections which can be made available to agents as a knowledge source.

## User Interaction
- **Web interface**: For setting up and managing agents and related configuration
- **REST API integration**: Primary method for integrating agents into larger systems

## Future (out of scope for now)
- **Observability**: Tracing and monitoring of agent runs
- **Prompt versioning**: Track and manage different versions of agent prompts
