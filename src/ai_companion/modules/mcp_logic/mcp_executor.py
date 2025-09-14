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
            
            # Extract the actual response content
            if hasattr(response, 'messages') and response.messages:
                # Get the last AI message
                last_message = response.messages[-1]
                result = last_message.content if hasattr(last_message, 'content') else str(last_message)
                logger.info(f"Agent response: {result}")
                return result
            else:
                logger.warning(f"Unexpected response format: {response}")
                return f"Task completed, but response format was unexpected: {str(response)}"
                
    except Exception as e:
        logger.error(f"MCP execution failed: {str(e)}", exc_info=True)
        return f"⚠️ MCP task failed: {str(e)}"