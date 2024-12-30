from langchain_core.messages import SystemMessage, RemoveMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ai_companion.graph.utils.state import AICompanionState
from ai_companion.graph.utils.helpers import get_router_chain, get_chat_model
from ai_companion.settings import settings


def router_node(state: AICompanionState):
    """Routes the conversation to the appropriate workflow based on the last message.
    
    Args:
        state (AICompanionState): The current state of the AI companion conversation.
            Contains message history and other contextual information.
    
    Returns:
        dict: A dictionary containing the workflow response.
            The 'workflow' key maps to the determined workflow path.
    """
    chain = get_router_chain()
    response = chain.invoke({"input": state["messages"][-1].content})
    return {"workflow": response}


def conversation_node(state: AICompanionState, config: RunnableConfig):
    """Handles the conversation workflow.
    
    Args:
        state (AICompanionState): The current state of the AI companion conversation.
            Contains message history and other contextual information.
    
    Returns:
        dict: A dictionary containing the conversation response.
    """
    model = get_chat_model()
    summary = state.get("summary", "")

    if summary:
        system_message = f"Summary of conversation earlier between Ava and the user: {summary}"
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else: 
        messages = state["messages"]
    
    response = model.ainvoke(messages, config)
    return {"messages": response}
    

async def image_node(state: AICompanionState, config: RunnableConfig):
    # TODO: Add here the logic for generating images
    return {"messages": state["messages"]}

async def audio_node(state: AICompanionState, config: RunnableConfig):
    # TODO: Add here the logic for generating audio
    return {"messages": state["messages"]}  


async def summarize_conversation(state: AICompanionState):
    
    model = get_chat_model()
    summary = state.get("summary", "")

    if summary:
        summary_message = (
            f"This is summary of the conversation to date between Ava and the user: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
        
    else:
        summary_message = "Create a summary of the conversation above between Ava and the user:"

    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = model.invoke(messages)
    
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-settings.NUMBER_OF_MESSAGES_TO_KEEP]]
    return {"summary": response.content, "messages": delete_messages}
