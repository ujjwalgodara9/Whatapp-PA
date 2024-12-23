import os
from io import BytesIO

import chainlit as cl
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_groq import ChatGroq

from speech_to_text import speech_to_text
from text_to_image import create_scenario, generate_image
from text_to_speech import text_to_speech


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session"""
    try:
        # Set up message history
        message_history = ChatMessageHistory()
        cl.user_session.set("message_history", message_history)

        # Set up the LLM with Groq
        model = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.3-70b-versatile",
            temperature=0.2,
        )

        # Set up the prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a friendly and helpful AI companion. 
                    Be concise, warm, and engaging in your responses.""",
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )

        # Create chain with message history
        chain = prompt | model | StrOutputParser()
        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: cl.user_session.get("message_history"),
            input_messages_key="question",
            history_messages_key="chat_history",
        )
        cl.user_session.set("chain", chain_with_history)

        # Send welcome message
        await cl.Message(content="Hello! I'm your AI companion. How can I help you today?").send()
    except Exception as e:
        await cl.Message(content=f"Error initializing chat: {str(e)}").send()
        raise


async def handle_image_scenario(prompt: str):
    """
    Generate and send a first-person scenario with matching image.

    Args:
        prompt: The user's prompt after "/image"
    """
    try:
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

    except Exception as e:
        await cl.Message(content=f"Error generating scenario: {str(e)}").send()
        raise


@cl.on_message
async def on_message(message: cl.Message):
    """Handle text messages"""
    # Check if message starts with "/image"
    if message.content.startswith("/image"):
        prompt = message.content[6:].strip()
        await handle_image_scenario(prompt)
        return

    # Handle regular text messages
    chain = cl.user_session.get("chain")
    message = cl.Message(content="")
    async with cl.Step(type="run"):
        async for chunk in chain.astream(
            {"question": message.content},
            {"configurable": {"session_id": cl.user_session.get("id")}},
        ):
            await message.stream_token(chunk)

    await message.send()


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

    # Generate response using chain with history
    chain = cl.user_session.get("chain")
    response = await chain.ainvoke(
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
