from __future__ import annotations

from .models import QueryStatus

TRANSITIONS: dict[QueryStatus, tuple[QueryStatus, ...]] = {
    QueryStatus.NEW: (QueryStatus.IN_PROGRESS, QueryStatus.CLOSED),
    QueryStatus.IN_PROGRESS: (
        QueryStatus.WAITING_CUSTOMER,
        QueryStatus.RESOLVED,
        QueryStatus.CLOSED,
    ),
    QueryStatus.WAITING_CUSTOMER: (
        QueryStatus.IN_PROGRESS,
        QueryStatus.RESOLVED,
        QueryStatus.CLOSED,
    ),
    QueryStatus.RESOLVED: (QueryStatus.CLOSED, QueryStatus.IN_PROGRESS),
    QueryStatus.CLOSED: (),
}


def allowed_transitions(status: QueryStatus) -> tuple[QueryStatus, ...]:
    return TRANSITIONS.get(status, ())


def can_transition(current: QueryStatus, new_status: QueryStatus) -> bool:
    return new_status in allowed_transitions(current)


def render_workflow_graph(output_format: str = "mermaid") -> str:
    normalized = output_format.strip().lower()
    if normalized == "mermaid":
        return _render_mermaid()
    if normalized == "dot":
        return _render_dot()
    if normalized == "text":
        return _render_text()
    raise ValueError("Format must be mermaid, dot, or text")


def _render_mermaid() -> str:
    lines = ["stateDiagram-v2", "    [*] --> NEW"]
    for source, targets in TRANSITIONS.items():
        for target in targets:
            lines.append(f"    {source.value} --> {target.value}")
    return "\n".join(lines)


def _render_dot() -> str:
    lines = ["digraph QueryWorkflow {", "  rankdir=LR;", "  node [shape=box];"]
    lines.append("  START [shape=circle, label=\"\"];\n")
    lines.append("  START -> NEW;")
    for source, targets in TRANSITIONS.items():
        for target in targets:
            lines.append(f"  {source.value} -> {target.value};")
    lines.append("}")
    return "\n".join(lines)


def _render_text() -> str:
    lines = ["Workflow:", "  START -> NEW"]
    for source, targets in TRANSITIONS.items():
        for target in targets:
            lines.append(f"  {source.value} -> {target.value}")
    return "\n".join(lines)
