"""Typed contracts for Trussium's bounded workflow HTTP API."""

from collections.abc import Mapping, Sequence
from typing import Literal, NotRequired, TypedDict


class ToolInvocation(TypedDict):
    """A declared registered-tool invocation."""

    name: str
    arguments: Mapping[str, object]


class WorkflowStep(TypedDict):
    """One named workflow step."""

    id: str
    invocation: ToolInvocation


class WorkflowRequest(TypedDict):
    """A bounded workflow request accepted by POST /v1/workflows/executions."""

    steps: Sequence[WorkflowStep]
    parallel_groups: NotRequired[Sequence[Sequence[WorkflowStep]]]
    deadline_seconds: NotRequired[float]
    depth: NotRequired[int]


class WorkflowStepResult(TypedDict):
    """The normalized output of one registered tool call."""

    tool_name: str
    output: dict[str, object]


class WorkflowResult(TypedDict):
    """A completed, timed-out, or cancelled bounded workflow result."""

    status: Literal["completed", "cancelled", "timed_out"]
    steps: Sequence[WorkflowStepResult]
