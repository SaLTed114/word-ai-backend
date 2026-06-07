from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app
from app.models import ActionPreview, ActionTarget, AgentPlan, SubAgentCall, TaskResponse, TextAction
from app.storage import AgentSessionStore


class MockAIClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def complete_task(self, prompt: str) -> TaskResponse:
        self.prompts.append(prompt)
        if "You are the main agent merging subagent outputs" in prompt:
            reply = "Main agent reply"
            final_text = None
            actions = []
            if "Proofread reply" in prompt and "Academic polish reply" in prompt:
                reply = "Proofread reply\n\nAcademic polish reply"
                final_text = "The findings demonstrate the result."
                actions = [
                    TextAction(id="proofread_action", type="replace_selection"),
                    TextAction(id="academic_action", type="replace_selection"),
                ]
            elif "Proofread reply" in prompt:
                reply = "Proofread reply"
                final_text = "the result"
                actions = [TextAction(id="proofread_action", type="replace_selection")]
            return TaskResponse(
                task="agent",
                reply=reply,
                summary="Merged from subagents: llm merge",
                actions=actions,
                final_text=final_text,
            )
        if "Subagent name: proofread" in prompt:
            return TaskResponse(
                task="agent",
                reply="Proofread reply",
                summary="proofread done",
                actions=[
                    TextAction(
                        id="proofread_action",
                        type="replace_selection",
                        target=ActionTarget(scope="selection"),
                        original="teh result",
                        replacement="the result",
                        preview=ActionPreview(before="teh result", after="the result"),
                        reason="Fix spelling.",
                        risk_level="low",
                        requires_confirmation=True,
                    )
                ],
                final_text="the result",
            )
        if "Subagent name: academic_polish" in prompt:
            return TaskResponse(
                task="agent",
                reply="Academic polish reply",
                summary="academic polish done",
                actions=[
                    TextAction(
                        id="academic_action",
                        type="replace_selection",
                        target=ActionTarget(scope="selection"),
                        original="the result",
                        replacement="The findings demonstrate the result.",
                        preview=ActionPreview(
                            before="the result",
                            after="The findings demonstrate the result.",
                        ),
                        reason="Improve academic tone.",
                        risk_level="medium",
                        requires_confirmation=True,
                    )
                ],
                final_text="The findings demonstrate the result.",
            )
        return TaskResponse(
            task="agent",
            reply="Main agent reply",
            summary="main agent done",
            actions=[],
            final_text=None,
        )

    async def complete_model(self, prompt: str, model_type):
        self.prompts.append(prompt)
        if model_type is AgentPlan:
            selected_skill = "custom-extra" if "custom-extra" in prompt else "proofread"
            return AgentPlan(
                calls=[
                    SubAgentCall(
                        name="custom_clarity_editor",
                        instruction="Improve clarity using only the selected text.",
                        reason="The user asked for clearer wording.",
                        skills=[selected_skill, "missing-skill"],
                    )
                ]
            )
        raise AssertionError(f"Unexpected model type: {model_type!r}")


def test_empty_subagents_uses_original_agent_flow(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        response = post_turn(client, session_id, {"message": "Help me revise this."})

    assert response.status_code == 200
    payload = response.json()["response"]
    assert payload["reply"] == "Main agent reply"
    assert len(ai_client.prompts) == 1
    assert "Subagent name:" not in ai_client.prompts[0]


def test_single_subagent_returns_task_response(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        response = post_turn(
            client,
            session_id,
            {
                "message": "Please check grammar.",
                "selection": {"text": "teh result"},
                "subagents": ["proofread"],
            },
        )

    assert response.status_code == 200
    payload = response.json()["response"]
    assert payload["task"] == "agent"
    assert payload["reply"] == "Proofread reply"
    assert payload["summary"].startswith("Merged from subagents:")
    assert payload["actions"][0]["id"] == "proofread_action"
    assert payload["actions"][0]["requires_confirmation"] is True
    assert "Check grammar, spelling, punctuation" in ai_client.prompts[0]
    assert "You are a meticulous proofreader." in ai_client.prompts[0]


def test_multiple_subagents_merge_actions_and_final_text(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        response = post_turn(
            client,
            session_id,
            {
                "message": "Proofread and polish.",
                "selection": {"text": "teh result"},
                "subagents": ["proofread", "academic_polish"],
            },
        )

    assert response.status_code == 200
    payload = response.json()["response"]
    assert payload["reply"] == "Proofread reply\n\nAcademic polish reply"
    assert [action["id"] for action in payload["actions"]] == ["proofread_action", "academic_action"]
    assert payload["final_text"] == "The findings demonstrate the result."


def test_custom_subagent_name_runs_without_registry_entry(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        response = post_turn(client, session_id, {"message": "Run it.", "subagents": ["custom_editor"]})
        messages = client.get(f"/agent/sessions/{session_id}/messages")

    assert response.status_code == 200
    payload = response.json()["response"]
    assert payload["summary"].startswith("Merged from subagents:")
    assert "Subagent name: custom_editor" in ai_client.prompts[0]
    assert len(messages.json()) == 2


def test_skills_field_still_reaches_main_agent_prompt(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        response = post_turn(
            client,
            session_id,
            {"message": "Use this skill.", "selection": {"text": "teh result"}, "skills": ["proofread"]},
        )

    assert response.status_code == 200
    assert len(ai_client.prompts) == 1
    prompt = ai_client.prompts[0]
    assert "Active skill instructions:" in prompt
    assert "You are a meticulous proofreader." in prompt
    assert "Subagent name:" not in prompt


def test_subagent_default_prompt_omits_full_history_but_includes_full_skill(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        post_turn(client, session_id, {"message": "Previous regular turn."})
        response = post_turn(
            client,
            session_id,
            {
                "message": "Please check grammar.",
                "selection": {
                    "text": "teh result",
                    "context": {"before": "Earlier context.", "after": "Later context."},
                },
                "subagents": ["proofread"],
            },
        )

    assert response.status_code == 200
    prompt = ai_client.prompts[-2]
    assert "Conversation history:" not in prompt
    assert "Previous regular turn." not in prompt
    assert "You are a meticulous proofreader." in prompt
    assert "Selected text:\nteh result" in prompt


def test_subagent_full_skill_prompt_can_be_explicitly_disabled(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        response = post_turn(
            client,
            session_id,
            {
                "message": "Please check grammar.",
                "selection": {"text": "teh result"},
                "subagents": ["proofread"],
                "use_full_skill_prompt": False,
            },
        )

    assert response.status_code == 200
    prompt = ai_client.prompts[0]
    assert "Skill instructions:" not in prompt
    assert "You are a meticulous proofreader." not in prompt


def test_auto_subagents_uses_planner_and_selected_skills(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        response = post_turn(
            client,
            session_id,
            {
                "message": "Make this clearer.",
                "selection": {"text": "teh result"},
                "skills": ["proofread"],
                "auto_subagents": True,
            },
        )

    assert response.status_code == 200
    payload = response.json()["response"]
    planner_prompt = ai_client.prompts[0]
    subagent_prompt = ai_client.prompts[1]
    assert payload["subagent_calls"] == [
        {
            "name": "custom_clarity_editor",
            "instruction": "Improve clarity using only the selected text.",
            "reason": "The user asked for clearer wording.",
            "skills": ["proofread"],
        }
    ]
    assert "low-cost subagent planner" in planner_prompt
    assert "Available skills:" in planner_prompt
    assert "Subagent name: custom_clarity_editor" in subagent_prompt
    assert "Instruction:\nImprove clarity using only the selected text." in subagent_prompt
    assert "Selected skills:\n- proofread" in subagent_prompt
    assert "missing-skill" not in subagent_prompt


def test_plan_endpoint_sees_new_non_preset_skill_and_planned_calls_execute(tmp_path: Path) -> None:
    custom_skill = PROJECT_ROOT / "skills" / "custom-extra.md"
    custom_skill.write_text("Use a custom extra editing checklist.", encoding="utf-8")
    ai_client = MockAIClient()
    try:
        with configured_client(tmp_path, ai_client) as client:
            session_id = create_session(client)
            plan_response = post_plan(
                client,
                session_id,
                {"message": "Make this clearer.", "selection": {"text": "teh result"}},
            )
            assert plan_response.status_code == 200
            plan = plan_response.json()
            response = post_turn(
                client,
                session_id,
                {
                    "message": "Make this clearer.",
                    "selection": {"text": "teh result"},
                    "planned_subagents": plan["calls"],
                },
            )
    finally:
        custom_skill.unlink(missing_ok=True)

    assert response.status_code == 200
    assert "custom-extra" in ai_client.prompts[0]
    assert response.json()["response"]["subagent_calls"][0]["skills"] == ["custom-extra"]
    assert "Selected skills:\n- custom-extra" in ai_client.prompts[1]


def test_stepwise_run_and_merge_endpoints(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        run_response = client.post(
            f"/agent/sessions/{session_id}/subagents/run",
            json={
                "message": "Please check grammar.",
                "selection": {"text": "teh result"},
                "subagent": {
                    "name": "proofread",
                    "instruction": "Check grammar.",
                    "skills": ["proofread"],
                },
            },
        )
        assert run_response.status_code == 200
        merge_response = client.post(
            f"/agent/sessions/{session_id}/subagents/merge",
            json={
                "message": "Please check grammar.",
                "selection": {"text": "teh result"},
                "subagent_results": [run_response.json()],
                "subagent_calls": [run_response.json()["response"]["subagent_calls"][0]],
            },
        )

    assert merge_response.status_code == 200
    payload = merge_response.json()["response"]
    assert payload["reply"] == "Proofread reply"
    assert payload["subagent_calls"][0]["skills"] == ["proofread"]


def test_llm_merge_uses_history_context_limit(tmp_path: Path) -> None:
    ai_client = MockAIClient()
    with configured_client(tmp_path, ai_client) as client:
        session_id = create_session(client)
        post_turn(client, session_id, {"message": "OLD_HISTORY_" + ("x" * 80)})
        response = post_turn(
            client,
            session_id,
            {
                "message": "Please check grammar.",
                "selection": {"text": "teh result"},
                "subagents": ["proofread"],
                "history_context_chars": 20,
            },
        )

    assert response.status_code == 200
    merge_prompt = ai_client.prompts[-1]
    assert "Conversation history:" in merge_prompt
    assert "OLD_HISTORY_" not in merge_prompt


@contextmanager
def configured_client(tmp_path: Path, ai_client: MockAIClient) -> Iterator[TestClient]:
    db_path = tmp_path / "agent_test.sqlite3"
    original_store_factory = main_module.AgentSessionStore
    main_module.AgentSessionStore = lambda: AgentSessionStore(db_path)  # type: ignore[assignment]
    try:
        with TestClient(app) as client:
            store = app.state.session_store
            store.initialize()
            app.state.ai_client = ai_client
            yield client
    finally:
        main_module.AgentSessionStore = original_store_factory


def create_session(client: TestClient) -> str:
    response = client.post("/agent/sessions", json={"title": "test"})
    assert response.status_code == 200
    return response.json()["id"]


def post_turn(client: TestClient, session_id: str, payload: dict) -> object:
    return client.post(f"/agent/sessions/{session_id}/messages", json=payload)


def post_plan(client: TestClient, session_id: str, payload: dict) -> object:
    return client.post(f"/agent/sessions/{session_id}/subagents/plan", json=payload)
