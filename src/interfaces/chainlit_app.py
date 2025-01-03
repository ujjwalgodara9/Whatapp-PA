from io import BytesIO

import chainlit as cl
from langchain_core.messages import AIMessageChunk, HumanMessage

from ai_companion.graph.agent import graph
from ai_companion.graph.utils.helpers import get_image_to_text_module
from ai_companion.modules.speech import SpeechToText
from ai_companion.modules.speech.text_to_speech import TextToSpeech


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session"""
    speech_to_text_module = SpeechToText()
    cl.user_session.set("speech_to_text", speech_to_text_module)


@cl.on_message
async def on_message(message: cl.Message):
    """Handle text messages and images"""
    msg = cl.Message(content="")

    # Process any attached images
    content = message.content
    if message.elements:
        image_to_text = get_image_to_text_module()

        for elem in message.elements:
            if isinstance(elem, cl.Image):
                # Read image file content
                with open(elem.path, "rb") as f:
                    image_bytes = f.read()

                # Analyze image and add to message content
                try:
                    description = await image_to_text.analyze_image(
                        image_bytes,  # Pass bytes instead of path
                        "Please describe what you see in this image in the context of our conversation.",
                    )
                    content += f"\n[Image Analysis: {description}]"
                except Exception as e:
                    cl.logger.warning(f"Failed to analyze image: {e}")

    # Process through graph with enriched message content
    async with cl.Step(type="run"):
        async for chunk in graph.astream(
            {"messages": [HumanMessage(content=content)]},
            {"configurable": {"thread_id": "1"}},
            stream_mode="messages",
        ):
            if chunk[1]["langgraph_node"] == "conversation_node" and isinstance(
                chunk[0], AIMessageChunk
            ):
                await msg.stream_token(chunk[0].content)

    output_state = graph.get_state(config={"configurable": {"thread_id": "1"}})

    if output_state.values.get("workflow") == "audio":
        response = output_state.values["messages"][-1].content
        audio_buffer = output_state.values["audio_buffer"]
        output_audio_el = cl.Audio(
            name="Audio",
            auto_play=True,
            mime="audio/mpeg3",
            content=audio_buffer,
        )
        await cl.Message(content=response, elements=[output_audio_el]).send()
    elif output_state.values.get("workflow") == "image":
        response = output_state.values["messages"][-1].content
        image = cl.Image(path=output_state.values["image_path"], display="inline")
        await cl.Message(content=response, elements=[image]).send()
    else:
        await msg.send()


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.AudioChunk):
    """Handle incoming audio chunks"""
    if chunk.isStart:
        buffer = BytesIO()
        buffer.name = f"input_audio.{chunk.mimeType.split('/')[1]}"
        cl.user_session.set("audio_buffer", buffer)
        cl.user_session.set("audio_mime_type", chunk.mimeType)
    cl.user_session.get("audio_buffer").write(chunk.data)


@cl.on_audio_end
async def on_audio_end(elements):
    """Process completed audio input"""
    # Get audio data
    audio_buffer = cl.user_session.get("audio_buffer")
    audio_buffer.seek(0)
    audio_data = audio_buffer.read()

    # Show user's audio message
    input_audio_el = cl.Audio(mime="audio/mpeg3", content=audio_data)
    await cl.Message(
        author="You", content="", elements=[input_audio_el, *elements]
    ).send()

    # Convert speech to text
    speech_to_text = cl.user_session.get("speech_to_text")
    transcription = await speech_to_text.transcribe(audio_data)

    output_state = await graph.ainvoke(
        {"messages": [HumanMessage(content=transcription)]},
        {"configurable": {"thread_id": "1"}},
    )

    audio_buffer = await TextToSpeech().synthesize(output_state["messages"][-1].content)

    output_audio_el = cl.Audio(
        name="Audio",
        auto_play=True,
        mime="audio/mpeg3",
        content=audio_buffer,
    )
    await cl.Message(
        content=output_state["messages"][-1].content, elements=[output_audio_el]
    ).send()
