"""Forwards CrewAI's internal events (agent start, LLM thoughts, tool use, tool results) to the UI queue.

CrewAI's event bus is global, so handlers are registered once and route to whichever queue is current.
"""
import queue

from crewai.events import (
    crewai_event_bus,
    AgentExecutionStartedEvent,
    LLMCallStartedEvent,
    LLMCallCompletedEvent,
    ToolUsageStartedEvent,
    ToolUsageFinishedEvent,
)

try:  # only present when Agent(reasoning=True) is used
    from crewai.events import AgentReasoningCompletedEvent
except ImportError:  # older versions
    AgentReasoningCompletedEvent = None

_state = {"q": None}


def set_queue(q: "queue.Queue | None") -> None:
    _state["q"] = q


def _emit(kind: str, text: str) -> None:
    q = _state["q"]
    if q is not None and text:
        q.put(("step", (kind, text)))


def _short(x, n=170) -> str:
    s = " ".join(str(x).split())
    return s if len(s) <= n else s[:n] + "…"


def _on_agent_start(source, event):
    _emit("start", f"{getattr(event, 'agent_role', 'Agent')} picked up the task")


def _on_llm_start(source, event):
    _emit("thought", f"Reasoning with {getattr(event, 'model', 'the model')}…")


def _on_llm_done(source, event):
    resp = getattr(event, "response", None)
    if resp is None:
        return
    text = resp if isinstance(resp, str) else str(resp)
    if not text.strip():
        return
    if "Thought:" in text:  # ReAct-style output
        thought = text.split("Thought:", 1)[1]
        for stop in ("Action:", "Final Answer:"):
            thought = thought.split(stop)[0]
        _emit("thought", _short(thought))
        if "Final Answer:" in text:
            _emit("answer", "Produced a final answer")
        return
    words = len(text.split())
    if words > 120:
        _emit("answer", f"Wrote a draft ({words} words)")
    else:
        _emit("thought", _short(text))


def _on_tool_start(source, event):
    _emit("tool", f"Using tool “{getattr(event, 'tool_name', '?')}” — {_short(getattr(event, 'tool_args', ''), 110)}")


def _on_tool_done(source, event):
    _emit("result", f"{getattr(event, 'tool_name', 'Tool')} returned: {_short(getattr(event, 'output', ''), 140)}")


def _on_reasoning(source, event):
    _emit("thought", "Plan: " + _short(getattr(event, "plan", ""), 200))


def register() -> None:
    if getattr(crewai_event_bus, "_quest_registered", False):
        return
    crewai_event_bus.on(AgentExecutionStartedEvent)(_on_agent_start)
    crewai_event_bus.on(LLMCallStartedEvent)(_on_llm_start)
    crewai_event_bus.on(LLMCallCompletedEvent)(_on_llm_done)
    crewai_event_bus.on(ToolUsageStartedEvent)(_on_tool_start)
    crewai_event_bus.on(ToolUsageFinishedEvent)(_on_tool_done)
    if AgentReasoningCompletedEvent is not None:
        crewai_event_bus.on(AgentReasoningCompletedEvent)(_on_reasoning)
    crewai_event_bus._quest_registered = True