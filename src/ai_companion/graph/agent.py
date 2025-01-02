from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ai_companion.graph.utils.edges import (
    select_workflow,
    should_summarize_conversation,
)
from ai_companion.graph.utils.nodes import (
    audio_node,
    conversation_node,
    image_node,
    router_node,
    summarize_conversation,
    context_injection_node,
)
from ai_companion.graph.utils.state import AICompanionState


@lru_cache
def create_workflow():
    workflow = StateGraph(AICompanionState)

    workflow.add_node("router_node", router_node)
    workflow.add_node("context_injection_node", context_injection_node)
    workflow.add_node("conversation_node", conversation_node)
    workflow.add_node("image_node", image_node)
    workflow.add_node("audio_node", audio_node)
    workflow.add_node("summarize_conversation", summarize_conversation)

    workflow.add_edge(START, "router_node")
    workflow.add_edge("router_node", "context_injection_node")
    workflow.add_conditional_edges("context_injection_node", select_workflow)
    workflow.add_conditional_edges("conversation_node", should_summarize_conversation)
    workflow.add_edge("summarize_conversation", END)

    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)

    return graph


graph = create_workflow()
