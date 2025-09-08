import os
import asyncio
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient, load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from ai_companion.settings import settings


logger = logging.getLogger(__name__)
 

llm = ChatOpenAI(model=settings.SMALL_MODEL, api_key=settings.OPENAI_API_KEY)

async def run_mcp_task(message: str) -> str:
    """
    Run a Playwright MCP task and return result as text.
    """
    client = MultiServerMCPClient(
        {
            "playwright": {
                "url": "http://host.docker.internal:8931/sse",  # Use SSE instead of WebSocket
                "transport": "sse",                              # Use SSE transport
            },
        }
    )

    async with client.session("playwright") as session:
        tools = await load_mcp_tools(session)
        agent = create_react_agent(model=llm, tools=tools)

        try:
            response = await agent.ainvoke({"messages": message})
            return str(response)
        except Exception as e:
            logger.error(f"MCP execution failed: {e}")
            return f"⚠️ MCP task failed: {str(e)}"