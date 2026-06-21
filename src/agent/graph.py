import logging
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from src.core.llm_factory import get_chat_model
from langchain_core.runnables import RunnableConfig

from src.config import settings
from src.agent.tools import policy_lookup_tool, create_leave_request_tool, update_crm_opportunity_tool

logger = logging.getLogger(__name__)

# List of tools to bind to the agent
TOOLS = [policy_lookup_tool, create_leave_request_tool, update_crm_opportunity_tool]

# Instantiate standard ToolNode
tool_node = ToolNode(TOOLS)

async def call_model(state: MessagesState, config: RunnableConfig):
    """
    Invokes the LLM with messages and bound tools.
    """
    logger.info("Agent call_model node invoked")
    
    # Retrieve pre-configured LLM from factory and bind tools
    llm = get_chat_model().bind_tools(TOOLS)
    
    # Run the model
    response = await llm.ainvoke(state["messages"], config=config)
    
    return {"messages": [response]}


# ── Graph Construction ────────────────────────────────────────────────────────

# Define a new StateGraph using MessagesState
workflow = StateGraph(MessagesState)

# Add nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Set entry point
workflow.add_edge(START, "agent")

# Add conditional edges from agent node
workflow.add_conditional_edges(
    "agent",
    tools_condition,
)

# Route tools node back to agent node
workflow.add_edge("tools", "agent")

# Memory Saver for tracking multi-turn conversation checkpoints in-memory
memory = MemorySaver()

# Compile the graph
agent_graph = workflow.compile(checkpointer=memory)
