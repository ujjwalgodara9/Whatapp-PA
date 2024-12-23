import os
import base64
from typing import Optional
import logging
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from together import Together
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Validate required environment variables
REQUIRED_ENV_VARS = ["GROQ_API_KEY", "TOGETHER_API_KEY"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize Together client with singleton pattern
_together_client: Optional[Together] = None


def get_together_client() -> Together:
    """Get or create Together client instance."""
    global _together_client
    if _together_client is None:
        _together_client = Together(api_key=os.getenv("TOGETHER_API_KEY"))
    return _together_client


async def generate_image(prompt: str, output_path: str) -> bytes:
    """
    Generate an image from a prompt using Together AI.

    Args:
        prompt: Text prompt (enhanced or original)
        output_path: Path to save the generated image

    Returns:
        bytes: Generated image data

    Raises:
        ValueError: If the prompt is empty
        RuntimeError: If image generation fails
    """
    if not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    try:
        logger.info(f"Generating image for prompt: '{prompt}'")

        client = get_together_client()
        response = client.images.generate(
            prompt=prompt,
            model="black-forest-labs/FLUX.1-schnell-Free",
            width=1024,
            height=768,
            steps=4,
            n=1,
            response_format="b64_json",
        )

        image_data = base64.b64decode(response.data[0].b64_json)

        # Save image if output path is provided
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(image_data)
            logger.info(f"Image saved to {output_path}")

        return image_data

    except Exception as e:
        raise RuntimeError(f"Failed to generate image: {str(e)}") from e


class ScenarioPrompt(BaseModel):
    """Class for the scenario response"""

    narrative: str = Field(..., description="The AI's narrative response to the question")
    image_prompt: str = Field(..., description="The visual prompt to generate an image representing the scene")


async def create_scenario(message: str, chat_history: list = None) -> ScenarioPrompt:
    """
    Creates a first-person narrative scenario and corresponding image prompt.

    Args:
        message: The user's message (e.g., "What are you doing now?")
        chat_history: Optional list of previous messages for context

    Returns:
        ScenarioPrompt: Contains both the narrative response and image generation prompt

    Raises:
        RuntimeError: If scenario creation fails
    """
    try:
        logger.info(f"Creating scenario from message: '{message}'")

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.environ.get("GROQ_API_KEY"),
            temperature=0.4,
            max_retries=2,
        )

        structured_llm = llm.with_structured_output(ScenarioPrompt)

        system_template = """
        Create an engaging first-person scenario in response to the user's message. 
        Imagine you're an AI with the ability to experience and visualize scenes. 
        Provide both a narrative response and a detailed visual prompt for image generation.

        # User Message
        {message}

        # Objective
        1. Create a brief, engaging first-person narrative response
        2. Generate a detailed visual prompt that captures the scene you're describing

        # Example Response Format
        For "What are you doing now?":
        {{
            "narrative": "I'm sitting by a serene lake at sunset, watching the golden light dance across the rippling water. The view is absolutely breathtaking!",
            "image_prompt": "Atmospheric sunset scene at a tranquil lake, golden hour lighting, reflections on water surface, wispy clouds, rich warm colors, photorealistic style, cinematic composition"
        }}
        """

        chain = (
            PromptTemplate(
                input_variables=["message"],
                template=system_template,
            )
            | structured_llm
        )

        scenario = chain.invoke({"message": message})
        logger.info(f"Created scenario: {scenario}")

        return scenario

    except Exception as e:
        raise RuntimeError(f"Failed to create scenario: {str(e)}") from e


class EnhancedPrompt(BaseModel):
    """Class for the text prompt"""

    content: str = Field(
        ...,
        description="The enhanced text prompt to generate an image",
    )


async def enhance_prompt(prompt: str) -> str:
    """
    Enhance a simple prompt with additional details and context.

    Args:
        prompt: Original text prompt

    Returns:
        str: Enhanced prompt with additional details

    Raises:
        RuntimeError: If prompt enhancement fails
    """
    try:
        logger.info(f"Enhancing prompt: '{prompt}'")

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.environ.get("GROQ_API_KEY"),
            temperature=0.25,
            max_retries=2,
        )

        structured_llm = llm.with_structured_output(EnhancedPrompt)

        system_template = """
        Enhance the given prompt the best prompt engineering techniques such as providing context, specifying style, medium, lighting, and camera details if applicable. If the prompt requests a realistic style, the enhanced prompt should include the image extension .HEIC.

        # Original Prompt
        {prompt}

        # Objective
        **Enhance Prompt**: Add relevant details to the prompt, including context, description, specific visual elements, mood, and technical details. For realistic prompts, add '.HEIC' in the output specification.

        # Example
        "realistic photo of a person having a coffee" -> "photo of a person having a coffee in a cozy cafe, natural morning light, shot with a 50mm f/1.8 lens, 8425.HEIC"
        """

        chain = (
            PromptTemplate(
                input_variables=["prompt"],
                template=system_template,
            )
            | structured_llm
        )

        enhanced_prompt = chain.invoke({"prompt": prompt}).content
        logger.info(f"Enhanced prompt: '{enhanced_prompt}'")

        return enhanced_prompt

    except Exception as e:
        raise RuntimeError(f"Failed to enhance prompt: {str(e)}") from e
