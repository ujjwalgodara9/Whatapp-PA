import os
from typing import Dict

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_groq import ChatGroq

# Dictionary to store all session histories
session_histories: Dict[str, ChatMessageHistory] = {}


def get_message_history(session_id: str) -> ChatMessageHistory:
    """
    Get or create a message history for a session

    Args:
        session_id: Unique identifier for the chat session
    """
    if session_id not in session_histories:
        session_histories[session_id] = ChatMessageHistory()
    return session_histories[session_id]


def get_runnable_with_history():
    """Create and configure the LangChain runnable with message history"""
    # Set up the LLM
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
    return RunnableWithMessageHistory(
        chain,
        get_message_history,
        input_messages_key="question",
        history_messages_key="chat_history",
    )
