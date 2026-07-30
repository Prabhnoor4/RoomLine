from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from app.agent.prompts import build_system_prompt
from app.agent.llm import get_llm
from app.agent.state import AgentState
from app.agent.tools import (
    cancel_wake_up_call,
    escalate_to_staff,
    get_order_status,
    get_room_service_menu,
    place_room_service_order,
    report_maintenance_issue,
    schedule_wake_up_call,
    submit_housekeeping_request,
)

TOOLS=[cancel_wake_up_call,
    escalate_to_staff,
    get_order_status,
    get_room_service_menu,
    place_room_service_order,
    report_maintenance_issue,
    schedule_wake_up_call,
    submit_housekeeping_request]

llm_with_tools= get_llm().bind_tools(TOOLS)

async def agent_node(state: AgentState) -> dict:
    # builds the message and returns the response by the agent
    system_message = {"role": "system", "content": build_system_prompt()}
    response = await llm_with_tools.ainvoke([system_message] + state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


workflow= StateGraph(AgentState)

workflow.add_node("agent",agent_node)
workflow.add_node("tools", ToolNode(TOOLS))

workflow.add_edge(START,"agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools","agent")

checkpointer = MemorySaver()
graph= workflow.compile(checkpointer=checkpointer)


