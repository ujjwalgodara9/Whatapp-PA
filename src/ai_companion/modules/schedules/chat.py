from typing import List

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_groq import ChatGroq

from ai_companion.settings import settings
from ai_companion.core.character_card import CHARACTER_CARD

class ChatModel:
    def __init__(self):
        """Initialize the ChatModel with Groq."""
        self.model = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.TEXT_MODEL_NAME,
            temperature=0.2,
        )
        
    def inject_context(self, context: str) -> None:
        # TODO: Implement context injection
        pass
    
    def build_system_prompt(self, summary: str) -> SystemMessage:
        system_prompt = CHARACTER_CARD
        
        if summary:
            system_prompt += f"\n\nThis is summary of the conversation earlier: {summary}"
        
        return SystemMessage(content=system_prompt)
    
    def answer(self, messages: List[AnyMessage]) -> str:
        system_prompt = self.build_system_prompt(messages)
        messages = [system_prompt] + messages
        return self.model.astream(messages)
