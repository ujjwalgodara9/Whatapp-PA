import os
from uuid import uuid4

from langchain_core.messages import HumanMessage, RemoveMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from ai_companion.graph.utils.chains import (
    get_character_response_chain,
    get_router_chain,
)
from ai_companion.graph.utils.helpers import (
    get_chat_model,
    get_text_to_speech_module,
    get_text_to_image_module,
)
from ai_companion.graph.utils.state import AICompanionState
from ai_companion.modules.schedules.context_generation import ScheduleContextGenerator
from ai_companion.settings import settings


async def router_node(state: AICompanionState):
    chain = get_router_chain()
    response = await chain.ainvoke({"messages": state["messages"][-5:]})
    return {"workflow": response}


def context_injection_node(state: AICompanionState):
    schedule_context = ScheduleContextGenerator.get_current_activity()
    if schedule_context != state.get("current_activity", ""):
        apply_activity = True
    else:
        apply_activity = False
    return {"apply_activity": apply_activity, "current_activity": schedule_context}


async def conversation_node(state: AICompanionState, config: RunnableConfig):
    current_activity = ScheduleContextGenerator.get_current_activity()
    chain = get_character_response_chain(state.get("summary", ""))

    response = await chain.ainvoke(
        {"messages": state["messages"], "current_activity": current_activity}, config
    )
    return {"messages": AIMessage(content=response)}


async def image_node(state: AICompanionState, config: RunnableConfig):
    current_activity = ScheduleContextGenerator.get_current_activity()
    chain = get_character_response_chain(state.get("summary", ""))
    text_to_image_module = get_text_to_image_module()

    response = await chain.ainvoke(
        {"messages": state["messages"], "current_activity": current_activity}, config
    )
    scenario = await text_to_image_module.create_scenario(response)

    os.makedirs("generated_images", exist_ok=True)
    img_path = f"generated_images/image_{str(uuid4())}.png"
    await text_to_image_module.generate_image(scenario.image_prompt, img_path)

    return {"messages": AIMessage(content=response), "image_path": img_path}


async def audio_node(state: AICompanionState, config: RunnableConfig):
    current_activity = ScheduleContextGenerator.get_current_activity()
    chain = get_character_response_chain(state.get("summary", ""))
    text_to_speech_module = get_text_to_speech_module()

    response = await chain.ainvoke(
        {"messages": state["messages"], "current_activity": current_activity}, config
    )
    output_audio = await text_to_speech_module.synthesize(response)

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
        summary_message = (
            "Create a summary of the conversation above between Ava and the user:"
        )

    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = await model.ainvoke(messages)

    delete_messages = [
        RemoveMessage(id=m.id)
        for m in state["messages"][: -settings.NUMBER_OF_MESSAGES_TO_KEEP]
    ]
    return {"summary": response.content, "messages": delete_messages}
