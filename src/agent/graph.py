import logging
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.runnables import RunnableConfig

from src.core.llm_factory import get_chat_model
from src.agent.registry import get_tools

logger = logging.getLogger(__name__)


def build_agent_graph(checkpointer: BaseCheckpointSaver | None = None):
    """
    Build and compile the agent graph.

    Args:
        checkpointer: Optional checkpoint saver. Defaults to in-memory.
                      Swap with PostgresSaver or RedisSaver for persistence.

    Returns:
        Compiled LangGraph CompiledStateGraph ready to invoke.
    """
    tools = get_tools()
    tool_node = ToolNode(tools)

    async def call_model(state: MessagesState, config: RunnableConfig):
        """Invoke the LLM with bound tools and current message state."""
        logger.info("Agent call_model node invoked")
        llm = get_chat_model().bind_tools(tools)
        response = await llm.ainvoke(state["messages"], config=config)
        return {"messages": [response]}

    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    saver = checkpointer or MemorySaver()
    return workflow.compile(checkpointer=saver)


# Default singleton graph — used by FastAPI and CLI
agent_graph = build_agent_graph()
