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
    result_str = create_leave_request_tool.invoke(
        {
            "employee_id": "emp_101",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "reason": "Family vacation",
        },
        config=config,
    )
    import json
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert "Leave request created successfully" in result["message"]
    assert result["details"]["employee_id"] == "emp_101"
    assert result["details"]["start_date"] == "2026-07-01"
    assert result["details"]["end_date"] == "2026-07-05"
    assert result["details"]["created_by"] == "hr_manager_1"


def test_create_leave_request_tool_sales_denied():
    config = {
        "configurable": {
            "user": UserContext(user_id="sales_rep_1", role="staff", department="Sales")
        }
    }
    result_str = create_leave_request_tool.invoke(
        {
            "employee_id": "emp_101",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "reason": "Family vacation",
        },
        config=config,
    )
    import json
    result = json.loads(result_str)
    assert result["status"] == "denied"
    assert result["error"] == "Access Denied"
    assert "restricted to HR department" in result["reason"]


# ── 2. update_crm_opportunity_tool Tests ──────────────────────────────────────

def test_update_crm_opportunity_tool_sales_success():
    config = {
        "configurable": {
            "user": UserContext(user_id="sales_lead", role="manager", department="Sales")
        }
    }
    result_str = update_crm_opportunity_tool.invoke(
        {
            "opp_id": "opp_999",
            "stage": "Proposal",
            "next_step": "Send technical contract review document",
        },
        config=config,
    )
    import json
    result = json.loads(result_str)
    assert result["status"] == "success"
    assert "updated successfully" in result["message"]
    assert result["details"]["opp_id"] == "opp_999"
    assert result["details"]["stage"] == "Proposal"
    assert result["details"]["updated_by"] == "sales_lead"


def test_update_crm_opportunity_tool_hr_denied():
    config = {
        "configurable": {
            "user": UserContext(user_id="hr_coordinator", role="staff", department="HR")
        }
    }
    result_str = update_crm_opportunity_tool.invoke(
        {
            "opp_id": "opp_999",
            "stage": "Proposal",
            "next_step": "Send proposal document",
        },
        config=config,
    )
    import json
    result = json.loads(result_str)
    assert result["status"] == "denied"
    assert result["error"] == "Access Denied"
    assert "restricted to Sales department" in result["reason"]


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

        result_str = policy_lookup_tool.invoke({"query": "leave policy"}, config=config)

        import json
        result = json.loads(result_str)
        assert result["status"] == "success"
        assert result["answer"] == "This is the retrieved corporate annual leave policy answer."
        assert result["grounding"] is True
        assert "Grounding Status: True" in result["raw_output"]
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
    # Mock get_chat_model so we don't trigger actual LLM model calls during unit test
    mock_get_llm = mocker.patch("src.agent.graph.get_chat_model")
    mock_instance = mock_get_llm.return_value
    
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

