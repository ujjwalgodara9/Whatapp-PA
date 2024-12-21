import os
from io import BytesIO
from typing import Tuple, BinaryIO

import chainlit as cl
from elevenlabs import ElevenLabs, Voice, VoiceSettings
from groq import Groq
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_groq import ChatGroq

# Initialize Groq client
groq_client = Groq()

# Initialize ElevenLabs client
elevenlabs_client = ElevenLabs()


@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session"""
    try:
        # Set up message history
        message_history = ChatMessageHistory()
        cl.user_session.set("message_history", message_history)

        # Validate API keys
        if not os.getenv("GROQ_API_KEY"):
            raise ValueError("GROQ_API_KEY not found in environment variables")
        if not os.getenv("ELEVENLABS_VOICE_ID"):
            raise ValueError("ELEVENLABS_VOICE_ID not found in environment variables")

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


@cl.on_message
async def on_message(message: cl.Message):
    """Handle text messages"""
    chain = cl.user_session.get("chain")
    message = cl.Message(content="")

    async with cl.Step(type="run"):
        async for chunk in chain.astream(
            {"question": message.content},
            {"configurable": {"session_id": cl.user_session.get("id")}},
        ):
            await message.stream_token(chunk)

    await message.send()


async def speech_to_text(audio_file: Tuple[str, bytes, str]) -> str:
    """Convert speech to text using Groq's Whisper

    Args:
        audio_file: Tuple containing (filename, binary_data, mime_type)

    Returns:
        str: Transcribed text
    """
    try:
        with open(audio_file[0], "wb") as f:
            f.write(audio_file[1])

        with open(audio_file[0], "rb") as f:
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_file[0], f.read()),
                model="whisper-large-v3-turbo",
                language="en",
                response_format="text",
            )
        return transcription
    finally:
        # Clean up temporary file
        if os.path.exists(audio_file[0]):
            os.remove(audio_file[0])


async def text_to_speech(text: str, mime_type: str) -> bytes:
    """Convert text to speech using ElevenLabs

    Args:
        text: Text to convert to speech
        mime_type: Output audio MIME type

    Returns:
        bytes: Audio data
    """
    try:
        audio_generator = elevenlabs_client.generate(
            text=text,
            voice=Voice(
                voice_id=os.getenv("ELEVENLABS_VOICE_ID"), settings=VoiceSettings(stability=0.5, similarity_boost=0.5)
            ),
            model="eleven_flash_v2",
        )

        # Convert generator to bytes
        audio_bytes = b"".join(audio_generator)
        return audio_bytes
    except Exception as e:
        raise RuntimeError(f"Text-to-speech conversion failed: {str(e)}")


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
    audio_file = audio_buffer.read()
    audio_mime_type = cl.user_session.get("audio_mime_type")

    # Show user's audio message
    input_audio_el = cl.Audio(mime="audio/mpeg3", content=audio_file)
    await cl.Message(author="You", content="", elements=[input_audio_el, *elements]).send()

    # Convert speech to text
    whisper_input = (audio_buffer.name, audio_file, audio_mime_type)
    transcription = await speech_to_text(whisper_input)

    # Generate response using chain with history
    chain = cl.user_session.get("chain")
    response = await chain.ainvoke(
        {"question": transcription},
        {"configurable": {"session_id": cl.user_session.get("id")}},
    )

    # Convert response to speech
    output_audio = await text_to_speech(response, "audio/mpeg3")

    # Send audio response
    output_audio_el = cl.Audio(
        name="Audio",
        auto_play=True,
        mime="audio/mpeg3",
        content=output_audio,
    )
    await cl.Message(content=response, elements=[output_audio_el]).send()
