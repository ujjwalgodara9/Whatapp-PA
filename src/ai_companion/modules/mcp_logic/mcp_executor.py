import os
import asyncio
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient, load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from ai_companion.settings import settings

logger = logging.getLogger(__name__)

llm = ChatOpenAI(model=settings.SMALL_MODEL, api_key=settings.OPENAI_API_KEY)

async def run_mcp_task(message: str) -> str:
    """
    Run a Playwright MCP task and return result as text.
    """
    try:
        client = MultiServerMCPClient(
            {
                "playwright": {
                    "url": "http://localhost:8931/sse",
                    "transport": "sse",
                },
            }
        )

        async with client.session("playwright") as session:
            logger.info("Connected to MCP server successfully")
            # Load tools from the MCP server
            tools = await load_mcp_tools(session)
            logger.info(f"Loaded {len(tools)} tools from MCP server")
            # Create the agent with the tools
            agent = create_react_agent(model=llm, tools=tools)
            # Format the message properly - agent expects messages list
            human_message = HumanMessage(content=message)
            # Invoke the agent
            logger.info(f"Invoking agent with message: {message}")
            response = await agent.ainvoke({"messages": [human_message]})

            # Defensive: handle dict or object with .messages
            messages = None
            if hasattr(response, 'messages'):
                messages = response.messages
            elif isinstance(response, dict) and 'messages' in response:
                messages = response['messages']

            if messages and isinstance(messages, list):
                # Only keep AI messages with non-empty content
                ai_messages = [m for m in messages if getattr(m, 'type', None) == 'ai' and getattr(m, 'content', None) and m.content.strip()]
                if ai_messages:
                    last_message = ai_messages[-1]
                    result = last_message.content.strip()
                else:
                    # Fallback: use last message with non-empty content
                    nonempty = [m for m in messages if getattr(m, 'content', None) and str(m.content).strip()]
                    if nonempty:
                        last_message = nonempty[-1]
                        result = str(getattr(last_message, 'content', last_message)).strip()
                    else:
                        last_message = messages[-1]
                        result = str(getattr(last_message, 'content', last_message)).strip()

                # If the message contains a file or screenshot, return a special marker
                if hasattr(last_message, 'additional_kwargs') and last_message.additional_kwargs:
                    file_url = last_message.additional_kwargs.get('file_url') or last_message.additional_kwargs.get('image_url')
                    if file_url:
                        return f"__MCP_FILE__::{file_url}::{result}"
                return result
            else:
                logger.warning(f"Unexpected response format: {response}")
                return f"Task completed, but response format was unexpected: {str(response)}"
    except Exception as e:
        logger.error(f"MCP execution failed: {str(e)}", exc_info=True)
        return f"⚠️ MCP task failed: {str(e)}"