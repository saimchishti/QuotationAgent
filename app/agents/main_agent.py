# agents/main_agent.py
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
import re
from core.config import llm

class AgentState(TypedDict):
    input: str
    intent: Optional[str]
    output: Optional[str]
    chat_history: Optional[list]

procedural_memory = """
You are an expert restaurant management assistant.
...
"""

def classify_intent(state: AgentState) -> AgentState:
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""{procedural_memory}

Conversation history:
{{chat_history}}

Classify as:
- information
- analytics
- consultancy
- action

Only return the lowercase label.
"""),
        ("human", "{user_input}")
    ])

    chain: Runnable = prompt | llm
    response = chain.invoke({
        "user_input": state["input"],
        "chat_history": state.get("chat_history", [])
    })

    state["intent"] = re.sub(r'[^a-z]', '', response.content.strip().lower())
    return state

# Import sub-agents
from agents.information_agent import get_information_agent_graph
from agents.analytics_agent import run_analytics_agent
from agents.consultant_agent import run_consultancy_agent
from agents.action_agent import run_action_agent

async def handle_information(state: AgentState) -> AgentState:
    info_state = {
        "input": state["input"],
        "chat_history": state.get("chat_history", [])
    }
    result = await get_information_agent_graph().ainvoke(info_state)
    state["output"] = result.get("output")
    state["chat_history"] = info_state["chat_history"]
    return state

def handle_analytics(state: AgentState) -> AgentState:
    state["output"] = run_analytics_agent(state["input"])
    return state

def handle_consultancy(state: AgentState) -> AgentState:
    state["output"] = run_consultancy_agent(state["input"])
    return state

def handle_action(state: AgentState) -> AgentState:
    state["output"] = run_action_agent(state["input"])
    return state

def get_main_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("information", handle_information)
    workflow.add_node("analytics", handle_analytics)
    workflow.add_node("consultancy", handle_consultancy)
    workflow.add_node("action", handle_action)

    workflow.set_entry_point("classify_intent")
    workflow.add_conditional_edges(
        "classify_intent",
        lambda state: state["intent"],
        {
            "information": "information",
            "analytics": "analytics",
            "consultancy": "consultancy",
            "action": "action",
        }
    )
    for node in ["information", "analytics", "consultancy", "action"]:
        workflow.add_edge(node, END)

    return workflow.compile()
