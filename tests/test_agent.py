import pytest
from unittest.mock import patch
from langchain_core.messages import AIMessage, HumanMessage

from src.auth.jwt_handler import UserContext
from src.agent.tools import (
    policy_lookup_tool,
    create_leave_request_tool,
    update_crm_opportunity_tool,
)
from src.agent.graph import agent_graph


# ── 1. create_leave_request_tool Tests ────────────────────────────────────────

def test_create_leave_request_tool_hr_success():
    config = {
        "configurable": {
            "user": UserContext(user_id="hr_manager_1", role="manager", department="HR")
        }
    }
    result = create_leave_request_tool.invoke(
        {
            "employee_id": "emp_101",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "reason": "Family vacation",
        },
        config=config,
    )
    assert "Success" in result
    assert "emp_101" in result
    assert "2026-07-01 to 2026-07-05" in result
    assert "HR Manager/Staff" in result


def test_create_leave_request_tool_sales_denied():
    config = {
        "configurable": {
            "user": UserContext(user_id="sales_rep_1", role="staff", department="Sales")
        }
    }
    result = create_leave_request_tool.invoke(
        {
            "employee_id": "emp_101",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "reason": "Family vacation",
        },
        config=config,
    )
    assert "Access Denied" in result
    assert "restricted to HR department" in result


# ── 2. update_crm_opportunity_tool Tests ──────────────────────────────────────

def test_update_crm_opportunity_tool_sales_success():
    config = {
        "configurable": {
            "user": UserContext(user_id="sales_lead", role="manager", department="Sales")
        }
    }
    result = update_crm_opportunity_tool.invoke(
        {
            "opp_id": "opp_999",
            "stage": "Proposal",
            "next_step": "Send technical contract review document",
        },
        config=config,
    )
    assert "Success" in result
    assert "opp_999" in result
    assert "Proposal" in result
    assert "Sales Agent" in result


def test_update_crm_opportunity_tool_hr_denied():
    config = {
        "configurable": {
            "user": UserContext(user_id="hr_coordinator", role="staff", department="HR")
        }
    }
    result = update_crm_opportunity_tool.invoke(
        {
            "opp_id": "opp_999",
            "stage": "Proposal",
            "next_step": "Send proposal document",
        },
        config=config,
    )
    assert "Access Denied" in result
    assert "restricted to Sales department" in result


# ── 3. policy_lookup_tool Tests ───────────────────────────────────────────────

def test_policy_lookup_tool_success():
    config = {
        "configurable": {
            "user": UserContext(user_id="user_any", role="staff", department="IT"),
            "search_engine": "mock_engine",
            "reranker": "mock_reranker",
            "generator": "mock_generator",
            "grounding_checker": "mock_checker",
            "retrieval_rail": "mock_rail",
        }
    }

    with patch("src.agent.tools.run_rag_pipeline") as mock_pipeline:
        mock_pipeline.return_value = {
            "answer": "This is the retrieved corporate annual leave policy answer.",
            "grounding": {"grounded": True, "reason": "Fully supported."},
            "results": [],
        }

        result = policy_lookup_tool.invoke({"query": "leave policy"}, config=config)

        assert "This is the retrieved corporate annual leave policy answer." in result
        assert "Grounding Status: True" in result
        mock_pipeline.assert_called_once_with(
            query="leave policy",
            user=config["configurable"]["user"],
            engine="mock_engine",
            reranker="mock_reranker",
            generator="mock_generator",
            grounding_checker="mock_checker",
            retrieval_rail="mock_rail",
        )


# ── 4. LangGraph agent_graph invocation Tests ─────────────────────────────────

@pytest.mark.anyio
async def test_agent_graph_invoke(mocker):
    # Mock ChatOpenAI so we don't trigger actual LLM model calls during unit test
    mock_chat = mocker.patch("src.agent.graph.ChatOpenAI")
    mock_instance = mock_chat.return_value
    
    # Mock response of the bound model's async ainvoke method
    mock_instance.bind_tools.return_value.ainvoke = mocker.AsyncMock(
        return_value=AIMessage(content="I have processed your hello message.")
    )

    config = {
        "configurable": {
            "thread_id": "test_session_123",
            "user": UserContext(user_id="dummy_user", role="staff", department="HR"),
        }
    }

    res = await agent_graph.ainvoke(
        {"messages": [HumanMessage(content="Hello agent")]},
        config=config,
    )

    assert "messages" in res
    assert len(res["messages"]) == 2
    assert res["messages"][-1].content == "I have processed your hello message."

