import json
import logging
from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.dependencies import (
    CurrentUser,
    SearchEngineDep,
    RerankerDep,
    GeneratorDep,
    GroundingDep,
    RetrievalRailDep,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Request / Response Schemas ────────────────────────────────────────────────

class AgentChatRequest(BaseModel):
    message: str = Field(..., description="Conversational query or instruction to the agent.")
    session_id: str = Field(..., description="Unique thread identifier to persist chat history.")


# ── Dependency Provider for Agent Graph ───────────────────────────────────────

def get_agent_graph(request: Request):
    """Retrieve the compiled LangGraph agent from application state."""
    return request.app.state.agent_graph


# ── Endpoint Handler ──────────────────────────────────────────────────────────

@router.post(
    "/chat",
    summary="Agentic conversation streaming with tool calling and memory"
)
async def chat_agent(
    body: AgentChatRequest = Body(...),
    current_user: CurrentUser = None,
    agent_graph = Depends(get_agent_graph),
    engine: SearchEngineDep = None,
    reranker: RerankerDep = None,
    generator: GeneratorDep = None,
    grounding: GroundingDep = None,
    retrieval_rail: RetrievalRailDep = None,
):
    """
    Agentic API endpoint returning Server-Sent Events (SSE):
    - Retains context between requests in the same session_id (thread_id).
    - Streams LLM tokens block-by-block.
    - Yields tool execution status updates (start and end).
    """
    logger.info(f"Agent SSE request from user={current_user.user_id} | session={body.session_id}")

    config = {
        "configurable": {
            "thread_id": body.session_id,
            "user": current_user,
            "search_engine": engine,
            "reranker": reranker,
            "generator": generator,
            "grounding_checker": grounding,
            "retrieval_rail": retrieval_rail,
        }
    }

    input_state = {
        "messages": [
            {
                "role": "user",
                "content": body.message
            }
        ]
    }

    async def event_generator():
        try:
            # Call LangGraph's astream_events using version 2 protocol
            async for event in agent_graph.astream_events(input_state, config=config, version="v2"):
                kind = event.get("event")
                name = event.get("name")

                # 1. Capture streaming chat model tokens
                if kind == "on_chat_model_stream" and event.get("metadata", {}).get("langgraph_node") == "agent":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and chunk.content:
                        yield f"data: {json.dumps({'event': 'token', 'text': chunk.content})}\n\n"

                # 2. Capture when a tool is triggered
                elif kind == "on_tool_start":
                    args = event.get("data", {}).get("input")
                    yield f"data: {json.dumps({'event': 'tool_start', 'tool': name, 'args': args})}\n\n"

                # 3. Capture when a tool completes execution
                elif kind == "on_tool_end":
                    output = event.get("data", {}).get("output")
                    yield f"data: {json.dumps({'event': 'tool_end', 'tool': name, 'output': str(output)})}\n\n"

            # End of stream event
            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Error in SSE streaming response: {e}")
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

