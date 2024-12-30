import os
from uuid import uuid4

from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ai_companion.graph.utils.helpers import get_chat_model, get_router_chain, get_text_to_speech_module
from ai_companion.graph.utils.state import AICompanionState
from ai_companion.settings import settings

from text_to_image import create_scenario, generate_image


async def router_node(state: AICompanionState):
    """Routes the conversation to the appropriate workflow based on the last message.
    
    Args:
        state (AICompanionState): The current state of the AI companion conversation.
            Contains message history and other contextual information.
    
    Returns:
        dict: A dictionary containing the workflow response.
            The 'workflow' key maps to the determined workflow path.
    """
    chain = get_router_chain()
    response = await chain.ainvoke({"input": state["messages"][-1].content})
    return {"workflow": response}


async def conversation_node(state: AICompanionState, config: RunnableConfig):
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
    
    response = await model.ainvoke(messages, config)
    return {"messages": response}
    

async def image_node(state: AICompanionState, config: RunnableConfig):
    model = get_chat_model()
    summary = state.get("summary", "")

    if summary:
        system_message = f"Summary of conversation earlier between Ava and the user: {summary}"
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else: 
        messages = state["messages"]
    
    response = await model.ainvoke(messages, config)
    scenario = await create_scenario(response.content)
    
    os.makedirs("generated_images", exist_ok=True)
    img_path = f"generated_images/image_{str(uuid4())}.png"
    await generate_image(scenario.image_prompt, img_path)
    
    return {"messages": response, "image_path": img_path}

async def audio_node(state: AICompanionState, config: RunnableConfig):
    """Handles the audio workflow.
    
    Args:
        state (AICompanionState): The current state of the AI companion conversation.
            Contains message history and other contextual information.
    
    Returns:
        dict: A dictionary containing the audio response.
    """
    model = get_chat_model()
    text_to_speech_module = get_text_to_speech_module()
    summary = state.get("summary", "")

    if summary:
        system_message = f"Summary of conversation earlier between Ava and the user: {summary}"
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else: 
        messages = state["messages"]
    
    response = await model.ainvoke(messages, config)
    output_audio = await text_to_speech_module.synthesize(response.content)
    
    return {"messages": response, "audio_buffer": output_audio}  


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
    response = await model.ainvoke(messages)
    
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-settings.NUMBER_OF_MESSAGES_TO_KEEP]]
    return {"summary": response.content, "messages": delete_messages}
