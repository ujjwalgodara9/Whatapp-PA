import os
import tempfile
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Validate required environment variables
REQUIRED_ENV_VARS = ["GROQ_API_KEY"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize Groq client with singleton pattern
_groq_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    """Get or create Groq client instance."""
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


async def speech_to_text(audio_data: bytes) -> str:
    """Convert speech to text using Groq's Whisper

    Args:
        audio_data: Binary audio data

    Returns:
        str: Transcribed text

    Raises:
        ValueError: If the audio file is empty or invalid
        RuntimeError: If the transcription fails
    """
    if not audio_data:
        raise ValueError("Audio data cannot be empty")

    try:
        # Create a temporary file with .wav extension
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name

        try:
            client = get_groq_client()
            # Open the temporary file for the API request
            with open(temp_file_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    language="en",
                    response_format="text",
                )

            if not transcription:
                raise RuntimeError("Transcription result is empty")

            return transcription

        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)

    except Exception as e:
        raise RuntimeError(f"Speech-to-text conversion failed: {str(e)}") from e
