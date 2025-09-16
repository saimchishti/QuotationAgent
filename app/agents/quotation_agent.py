"""
quotation_agent.py
------------------
LangGraph agent for generating quotations from Mongo draft orders.
"""

import asyncio
import json
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from app.tools.quotationagent_tools import (
    fetch_draft_orders_tool,
    validate_draft_items_tool,
)
from app.services.quotation_agent_services import generate_quotation
from app.core.config import settings


# ==============================
# LLM Setup (Groq API)
# ==============================
llm = ChatOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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",
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.3,
)


# ==============================
# Wrap generate_quotation into a tool
# ==============================
from langchain_core.tools import tool

@tool("generate_quotation")
async def generate_quotation_tool(draft_json: str) -> str:
    """
    Generate a quotation from a draft order JSON string.
    Performs availability check in Postgres and calls LLM.
    """
    try:
        draft = json.loads(draft_json)
    except Exception as e:
        return json.dumps({"error": f"Invalid draft JSON: {e}"})

    quotation = await generate_quotation(draft)
    return json.dumps(quotation, default=str)


# ==============================
# Build LangGraph Agent
# ==============================
tools = [
    fetch_draft_orders_tool,
    validate_draft_items_tool,
    generate_quotation_tool,
]

agent_executor = create_react_agent(
    llm,
    tools,
    debug=True,   # shows reasoning and tool calls
)


# ==============================
# Example Execution
# ==============================
async def main():
    print("🤖 Running Quotation Agent...\n")

    result = await agent_executor.ainvoke(
        {"messages": [("user", "Fetch a draft order, validate its items, and generate a quotation")]}
    )

    print("\n=== FINAL RESULT ===")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
