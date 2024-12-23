import os
from io import BytesIO

import chainlit as cl

from langchain_runnable import get_runnable_with_history
from speech_to_text import speech_to_text
from text_to_image import create_scenario, generate_image
from text_to_speech import text_to_speech


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session"""
    await cl.Message(content="Hello! I'm your AI companion. How can I help you today?").send()


async def handle_image_scenario(prompt: str):
    """
    Generate and send a first-person scenario with matching image.

    Args:
        prompt: The user's prompt after "/image"
    """
    # Create scenario and generate image
    scenario = await create_scenario(prompt)

    # Generate and save image
    os.makedirs("generated_images", exist_ok=True)
    img_path = f"generated_images/image_{cl.user_session.get('id')}.png"
    # enhanced_prompt = await enhance_prompt(scenario.image_prompt)
    await generate_image(scenario.image_prompt, img_path)

    # Send response with image
    image = cl.Image(path=img_path, display="inline")
    await cl.Message(content=scenario.narrative, elements=[image]).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle text messages"""
    # Check if message starts with "/image"
    if message.content.startswith("/image"):
        prompt = message.content[6:].strip()
        await handle_image_scenario(prompt)
        return

    # Handle regular text messages
    runnable = get_runnable_with_history()
    msg = cl.Message(content="")
    async with cl.Step(type="run"):
        async for chunk in runnable.astream(
            {"question": message.content},
            {"configurable": {"session_id": cl.user_session.get("id")}},
        ):
            await msg.stream_token(chunk)

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
    await cl.Message(author="You", content="", elements=[input_audio_el, *elements]).send()

    # Convert speech to text
    transcription = await speech_to_text(audio_data)

    # Generate response using runnable with history
    runnable = get_runnable_with_history()
    response = await runnable.ainvoke(
        {"question": transcription},
        {"configurable": {"session_id": cl.user_session.get("id")}},
    )

    # Convert response to speech
    output_audio = await text_to_speech(response)

    # Send audio response
    output_audio_el = cl.Audio(
        name="Audio",
        auto_play=True,
        mime="audio/mpeg3",
        content=output_audio,
    )
    await cl.Message(content=response, elements=[output_audio_el]).send()
