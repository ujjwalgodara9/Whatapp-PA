from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from ai_companion.core.prompts import ROUTER_PROMPT
from ai_companion.settings import settings
from ai_companion.modules.speech import TextToSpeech


def get_chat_model():
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.TEXT_MODEL_NAME,
    )   


def get_router_chain():
    model = get_chat_model()

    prompt = ChatPromptTemplate.from_messages([
        ("system", ROUTER_PROMPT),
        ("human", "{input}"),
    ])
    
    return prompt | model | StrOutputParser()


def get_text_to_speech_module():
    return TextToSpeech()
