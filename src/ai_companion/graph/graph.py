from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from ai_companion.graph.edges import (
    select_workflow,
    should_summarize_conversation,
)
from ai_companion.graph.nodes import (
    audio_node,
    conversation_node,
    image_node,
    router_node,
    summarize_conversation_node,
    context_injection_node,
)
from ai_companion.graph.state import AICompanionState


@lru_cache(maxsize=1)
def create_workflow_graph():
    graph_builder = StateGraph(AICompanionState)

    graph_builder.add_node("router_node", router_node)
    graph_builder.add_node("context_injection_node", context_injection_node)
    graph_builder.add_node("conversation_node", conversation_node)
    graph_builder.add_node("image_node", image_node)
    graph_builder.add_node("audio_node", audio_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)

    graph_builder.add_edge(START, "router_node")
    graph_builder.add_edge("router_node", "context_injection_node")
    graph_builder.add_conditional_edges("context_injection_node", select_workflow)
    graph_builder.add_conditional_edges(
        "conversation_node", should_summarize_conversation
    )
    graph_builder.add_edge("summarize_conversation_node", END)

    return graph_builder
