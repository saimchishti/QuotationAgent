# agent_runner.py
import asyncio
from agents.main_agent import get_main_agent_graph
from langsmith.run_helpers import trace   # ✅ LangSmith import

# Build the agent graph
main_agent_app = get_main_agent_graph()

async def run_main_agent(user_input: str):
    # ✅ Create a top-level trace for this user interaction
    with trace(
        "main_agent_call",
        run_type="chain",
        metadata={"user_input": user_input}
    ) as run:
        state = {"input": user_input}
        result = await main_agent_app.ainvoke(state)

        # ✅ Record the final output in the trace
        run.end(outputs=result)
        return result

if __name__ == "__main__":
    print("🔁 Main Agent is running. Type 'exit' to quit.\n")
    try:
        while True:
            user_input = input("🧑 You: ")
            if user_input.strip().lower() == "exit":
                break
            try:
                response = asyncio.run(run_main_agent(user_input))
                print("🤖 Agent:", response.get("output", "[No Output]"))
            except Exception as e:
                print("❌ Error: Intent was not Recognised, please try again.", str(e))
    finally:
        print()
