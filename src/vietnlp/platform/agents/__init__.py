"""Sub-agent layer: routed, cached, budget-capped model access.

Import surface is deliberately small. Pipeline code uses `AgentClient` + `registry.get`
and never constructs a model name or reads pricing directly.
"""

from .budget import BudgetExceeded, BudgetLedger
from .cache import ResponseCache
from .client import AgentClient, DeepSeekError, Result
from .policy import Model, Route, UnknownTask, all_tasks, estimate_usd, route
from .registry import AGENTS, Agent, ValidationFailed, get

__all__ = [
    "AGENTS", "Agent", "AgentClient", "BudgetExceeded", "BudgetLedger",
    "DeepSeekError", "Model", "ResponseCache", "Result", "Route", "UnknownTask",
    "ValidationFailed", "all_tasks", "estimate_usd", "get", "route",
]
