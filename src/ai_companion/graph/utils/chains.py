from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from ai_companion.core.prompts import CHARACTER_CARD_PROMPT, ROUTER_PROMPT
from ai_companion.graph.utils.helpers import AsteriskRemovalParser, get_chat_model


def get_router_chain():
    model = get_chat_model()

    prompt = ChatPromptTemplate.from_messages(
        [("system", ROUTER_PROMPT), MessagesPlaceholder(variable_name="messages")]
    )

    return prompt | model | StrOutputParser()


def get_character_response_chain(summary: str = ""):
    model = get_chat_model()
    system_message = CHARACTER_CARD_PROMPT

    if summary:
        system_message += (
            f"\n\nSummary of conversation earlier between Ava and the user: {summary}"
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    return prompt | model | AsteriskRemovalParser()
