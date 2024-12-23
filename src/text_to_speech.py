import os
from elevenlabs import ElevenLabs, Voice, VoiceSettings
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Validate required environment variables
REQUIRED_ENV_VARS = ["ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize ElevenLabs client with singleton pattern
_elevenlabs_client: Optional[ElevenLabs] = None


def get_elevenlabs_client() -> ElevenLabs:
    """Get or create ElevenLabs client instance."""
    global _elevenlabs_client
    if _elevenlabs_client is None:
        _elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    return _elevenlabs_client


async def text_to_speech(text: str) -> bytes:
    """Convert text to speech using ElevenLabs

    Args:
        text: Text to convert to speech

    Returns:
        bytes: Audio data

    Raises:
        ValueError: If the input text is empty or too long
        RuntimeError: If the text-to-speech conversion fails
    """
    if not text.strip():
        raise ValueError("Input text cannot be empty")

    if len(text) > 5000:  # ElevenLabs typical limit
        raise ValueError("Input text exceeds maximum length of 5000 characters")

    try:
        client = get_elevenlabs_client()
        audio_generator = client.generate(
            text=text,
            voice=Voice(
                voice_id=os.getenv("ELEVENLABS_VOICE_ID"), settings=VoiceSettings(stability=0.5, similarity_boost=0.5)
            ),
            model="eleven_flash_v2",
        )

        # Convert generator to bytes
        audio_bytes = b"".join(audio_generator)
        if not audio_bytes:
            raise RuntimeError("Generated audio is empty")

        return audio_bytes

    except Exception as e:
        raise RuntimeError(f"Text-to-speech conversion failed: {str(e)}") from e
