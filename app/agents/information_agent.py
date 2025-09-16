from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from langchain_core.tools import Tool, BaseTool
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory
import re

from tools.informer_tools import (
    order_volume_tracker_tool, order_frequency_tool, employee_roster_tool,
    employee_shift_tool, attendance_tracker_tool, payroll_summary_tool,
    purchase_orders_tool, supplier_orders_tool, order_cost_breakdown_tool,
    pending_deliveries_tool, received_inventory_log_tool, rejected_orders_log_tool,
    menu_items_tool, menu_categories_tool, item_availability_tool,
    price_history_tool, inventory_overview_tool, inventory_expiry_tool,
    inventory_cost_breakdown_tool, inventory_by_supplier_or_brand_tool,
    daily_wastage_log_tool, order_to_waste_correlation_tool, vendor_directory_tool,
    ingredient_vendor_mapper_tool, vendor_performance_tracker_tool,
    ingredient_sourcing_optimizer_tool, vendor_branch_linkage_tool,
)
from core.constants import business_owner_id
from core.config import llm

# === State ===
class InfoAgentState(TypedDict, total=False):
    input: str
    tool_name: Optional[str]
    output: Optional[str]
    chat_history: Optional[list]

# === Tool Mapping ===
tool_mapping: dict[str, Tool] = {
    "order_volume": order_volume_tracker_tool,
    "order_frequency": order_frequency_tool,
    "employee_roster": employee_roster_tool,
    "employee_shift": employee_shift_tool,
    "attendance": attendance_tracker_tool,
    "payroll": payroll_summary_tool,
    "purchase_orders": purchase_orders_tool,
    "supplier_orders": supplier_orders_tool,
    "order_cost": order_cost_breakdown_tool,
    "pending_deliveries": pending_deliveries_tool,
    "received_inventory": received_inventory_log_tool,
    "rejected_orders": rejected_orders_log_tool,
    "menu_items": menu_items_tool,
    "menu_categories": menu_categories_tool,
    "item_availability": item_availability_tool,
    "price_history": price_history_tool,
    "inventory_overview": inventory_overview_tool,
    "inventory_expiry": inventory_expiry_tool,
    "inventory_cost": inventory_cost_breakdown_tool,
    "inventory_supplier": inventory_by_supplier_or_brand_tool,
    "wastage": daily_wastage_log_tool,
    "waste_correlation": order_to_waste_correlation_tool,
    "vendor_directory": vendor_directory_tool,
    "ingredient_vendor": ingredient_vendor_mapper_tool,
    "vendor_performance": vendor_performance_tracker_tool,
    "sourcing_optimizer": ingredient_sourcing_optimizer_tool,
    "vendor_linkage": vendor_branch_linkage_tool,
}

# === Improved Tool Selection Prompt ===
tool_select_prompt = ChatPromptTemplate.from_template("""
You are an intelligent reasoning agent named Information.
Your task: Select EXACTLY ONE tool from the list below that is best suited to answer the user's query.

**Conversation history (use this to resolve pronouns and references):**
{chat_history}

**Available Tools:**
attendance: Track daily attendance and employee check-ins  
employee_roster: Get the list of all employees and their roles  
employee_shift: View the shift schedule and assignment of employees  
ingredient_vendor: Map ingredients to the vendors that supply them  
inventory_cost: Break down inventory cost across categories or items  
inventory_expiry: Find inventory items that are near or past their expiry date  
inventory_overview: Get current levels and quantities of all inventory ingredients  
inventory_supplier: View inventory organized by supplier or brand  
item_availability: Check which menu items are unavailable due to missing ingredients  
menu_categories: Retrieve the menu categories and their details  
menu_items: List of available menu items  
order_cost: Break down costs associated with each order  
order_frequency: Analyze how frequently orders are being placed  
order_volume: Track the total volume of orders placed over a given period  
payroll: Generate payroll summaries for all employees  
pending_deliveries: List all deliveries that are pending or in-transit  
price_history: View the historical pricing of ingredients or items  
purchase_orders: Retrieve a list of all purchase orders placed  
received_inventory: Log of all received inventory items  
rejected_orders: View all rejected supplier or purchase orders  
sourcing_optimizer: Recommend best vendors for ingredient sourcing based on cost and performance  
supplier_orders: Fetch all orders made to suppliers  
vendor_branch_linkage: View relationships between vendors and branches they supply  
vendor_directory: List all vendors available in the system  
vendor_performance: Track and evaluate vendor performance metrics  
wastage: View daily log of food and ingredient wastage  
waste_correlation: Analyze correlation between orders and resulting wastage  

**User Query:**
{input}

**Instructions:**
1. If the user query contains pronouns (he, she, they, it, them), resolve them to the correct entity based on conversation history.
2. Identify which tool best matches the user’s request. Choose the one that directly provides the needed data or action.
3. If more than one tool is relevant, choose the one that would be most specific to the request.
4. Output ONLY the tool name EXACTLY as it appears in the list above.
5. If no tool applies, output "none".

Return ONLY the tool name — no explanation, no punctuation, no extra text.
""")


chain: Runnable = tool_select_prompt | llm | StrOutputParser()

from langchain.memory import ConversationEntityMemory
# === Route Tool ===
async def route_tool(state: InfoAgentState) -> InfoAgentState:
    memory = ConversationEntityMemory(
        llm=llm,
        input_key="input",
        memory_key="chat_history"
    )
    memory.chat_memory.messages = state.get("chat_history", [])

    response = await chain.ainvoke({
        "input": state["input"],
        "chat_history": state.get("chat_history", []),
    })

    memory.save_context({"input": state["input"]}, {"output": response})
    state["chat_history"] = memory.chat_memory.messages
    state["tool_name"] = re.sub(r'[^a-z_]', '', response.strip().lower())
    return state


# === Run Tool ===
async def run_tool(state: InfoAgentState) -> InfoAgentState:
    tool_name = state["tool_name"]
    tool = tool_mapping.get(tool_name)

    if not isinstance(tool, BaseTool):
        raise ValueError(f"Tool '{tool_name}' not found or invalid.")

    args = {"business_owner_id": business_owner_id}
    result = await tool.ainvoke(args)
    state["output"] = result
    return state

# === Filter Output ===
async def filter_output(state: InfoAgentState) -> InfoAgentState:
    memory = ConversationEntityMemory(
        llm=llm,
        input_key="input",
        memory_key="chat_history"
    )
    memory.chat_memory.messages = state.get("chat_history", [])

    prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant. The user asked a question, and you've received raw data from a tool. 
You will extract the required information from the raw data without making assumptions, 
and without altering letters, names, or numbers.

User Query: {input}
Chat History: {chat_history}
Tool Output: {tool_output}

Extract the most relevant information and give a concise answer:
""")
    
    chain = prompt | llm | StrOutputParser()
    
    filtered = await chain.ainvoke({
        "input": state["input"],
        "chat_history": state.get("chat_history", []),
        "tool_output": state["output"]
    })

    memory.save_context({"input": state["input"]}, {"output": filtered})
    state["chat_history"] = memory.chat_memory.messages
    state["output"] = filtered
    return state

# === Build Graph ===
def get_information_agent_graph():
    workflow = StateGraph(InfoAgentState)
    workflow.add_node("route_tool", RunnableLambda(route_tool))
    workflow.add_node("run_tool", RunnableLambda(run_tool))
    workflow.add_node("filter_output", RunnableLambda(filter_output))

    workflow.set_entry_point("route_tool")
    workflow.add_edge("route_tool", "run_tool")
    workflow.add_edge("run_tool", "filter_output")
    workflow.add_edge("filter_output", END)

    return workflow.compile()
