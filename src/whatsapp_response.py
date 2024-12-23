import logging
import os
from fastapi import APIRouter, Request, Response
import httpx
from io import BytesIO
from typing import Dict

from langchain_runnable import get_runnable_with_history
from speech_to_text import speech_to_text
from text_to_speech import text_to_speech
from text_to_image import create_scenario, generate_image

# Configure logger
logger = logging.getLogger(__name__)

# Router for WhatsApp response
whatsapp_router = APIRouter()

# WhatsApp API credentials
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")


@whatsapp_router.api_route("/whatsapp_response", methods=["GET", "POST"])
async def whatsapp_handler(request: Request) -> Response:
    """Handles incoming messages and status updates from the WhatsApp Cloud API."""

    if request.method == "GET":
        params = request.query_params
        if params.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN"):
            return Response(content=params.get("hub.challenge"), status_code=200)
        return Response(content="Verification token mismatch", status_code=403)

    try:
        data = await request.json()
        change_value = data["entry"][0]["changes"][0]["value"]
        if "messages" in change_value:
            message = change_value["messages"][0]
            from_number = message["from"]
            session_id = from_number

            # Get user message
            if message["type"] == "audio":
                message_text = await process_audio_message(message)
            else:
                message_text = message["text"]["body"]

            # Check if message starts with /image
            if message_text.startswith("/image"):
                prompt = message_text[6:].strip()
                success = await handle_image_scenario(from_number, prompt)
                if not success:
                    return Response(content="Failed to send image", status_code=500)
                return Response(content="Image processed", status_code=200)

            # Get runnable with message history
            runnable = get_runnable_with_history()

            # Process message with the runnable
            response_text = await runnable.ainvoke(
                {"question": message_text},
                {"configurable": {"session_id": session_id}},
            )

            # Send response
            success = await send_response(from_number, response_text, message["type"])

            if not success:
                return Response(content="Failed to send message", status_code=500)

            return Response(content="Message processed", status_code=200)

        elif "statuses" in change_value:
            return Response(content="Status update received", status_code=200)

        else:
            return Response(content="Unknown event type", status_code=400)

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return Response(content="Internal server error", status_code=500)


async def process_audio_message(message: Dict) -> str:
    """Download and transcribe audio message."""
    audio_id = message["audio"]["id"]
    media_metadata_url = f"https://graph.facebook.com/v21.0/{audio_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    async with httpx.AsyncClient() as client:
        metadata_response = await client.get(media_metadata_url, headers=headers)
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        download_url = metadata.get("url")

    # Download the audio file
    async with httpx.AsyncClient() as client:
        audio_response = await client.get(download_url, headers=headers)
        audio_response.raise_for_status()

    # Prepare for transcription
    audio_buffer = BytesIO(audio_response.content)
    audio_buffer.seek(0)
    audio_data = audio_buffer.read()

    return await speech_to_text(audio_data)


async def send_response(from_number: str, response_text: str, message_type: str = "text") -> bool:
    """Send response to user via WhatsApp API."""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    if message_type == "audio":
        try:
            audio_response = await text_to_speech(response_text)
            media_id = await upload_media(audio_response, "audio/mpeg")
            json_data = {
                "messaging_product": "whatsapp",
                "to": from_number,
                "type": "audio",
                "audio": {"id": media_id},
            }
        except Exception as e:
            logger.error(f"Audio generation failed, falling back to text: {e}")

    else:  # Text message
        json_data = {
            "messaging_product": "whatsapp",
            "to": from_number,
            "type": "text",
            "text": {"body": response_text},
        }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages", headers=headers, json=json_data
        )

    return response.status_code == 200


async def upload_media(media_content: BytesIO, mime_type: str) -> str:
    """Upload media to WhatsApp servers."""
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    files = {"file": ("response.mp3", media_content, mime_type)}
    data = {"messaging_product": "whatsapp", "type": mime_type}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/media",
            headers=headers,
            files=files,
            data=data,
        )
        result = response.json()

    if "id" not in result:
        raise Exception("Failed to upload media")
    return result["id"]


async def handle_image_scenario(from_number: str, prompt: str) -> bool:
    """Generate and send an image scenario via WhatsApp."""
    try:
        # Create scenario
        scenario = await create_scenario(prompt)

        # Generate image
        image_data = await generate_image(scenario.image_prompt, output_path="")

        # Upload image to WhatsApp
        media_content = BytesIO(image_data)
        media_id = await upload_media(media_content, "image/png")

        # Send image with scenario text
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        json_data = {
            "messaging_product": "whatsapp",
            "to": from_number,
            "type": "image",
            "image": {"id": media_id, "caption": scenario.narrative},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers=headers,
                json=json_data,
            )

        return response.status_code == 200

    except Exception as e:
        logger.error(f"Error in handle_image_scenario: {e}")
        return False
