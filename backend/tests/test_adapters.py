from copy import deepcopy
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from backend.engine import derive
from backend.main import create_app
from backend.providers import ObservationBatch, GeminiProvider, ProviderError, configured_provider, validated_observations
from backend.repository import JsonRepository, MongoRepository, demo_state


@pytest.fixture
def snapshot():
    state = demo_state()
    for d in state["documents"]:
        d["processed"] = True
    return derive(state)


def observation():
    return {"title": "Birth-year discrepancy needs corroboration", "description": "The birth register reports 1971; compare the independent notice before relying on the year.", "person_ids": ["clara"], "citations": [{"document_id": "d05", "quote": "Clara Mercer was born in 1971 in Trenton, New Jersey.", "start_line": 2, "end_line": 2}]}


def test_model_observations_require_real_spans_known_people_and_cautious_claims(snapshot):
    valid = observation()
    accepted, rejected = validated_observations({"observations": [valid]}, snapshot, "test")
    assert len(accepted) == 1 and rejected == 0
    assert accepted[0]["title"].startswith("Model suggestion")
    for invalid in [{**valid, "person_ids": ["invented"]}, {**valid, "title": "Confirmed identity"}, {**valid, "description": "Confidence 99%"}, {**valid, "citations": [{**valid["citations"][0], "start_line": 1, "end_line": 1}]}]:
        with pytest.raises(ProviderError):
            validated_observations({"observations": [invalid]}, snapshot, "test")
    next(d for d in snapshot["documents"] if d["id"] == "d05")["processed"] = False
    with pytest.raises(ProviderError):
        validated_observations({"observations": [valid]}, snapshot, "test")


def test_gemini_adapter_sends_schema_and_checks_returned_citations_offline(snapshot):
    pytest.importorskip("google.genai")
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(parsed=ObservationBatch.model_validate({"observations": [observation()]}))

    adapter = GeminiProvider("offline-test", "explicit-model", SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    result, trace = adapter.extract(snapshot, "Compare birth years")
    assert len(result) == 1 and "structured extraction" in trace[0]
    assert calls[0]["config"].response_schema is ObservationBatch
    assert '"line": 2' in calls[0]["contents"]
    assert snapshot["candidates"][0]["status"] == "excluded"  # deterministic DNA check, unaffected by the model


def test_missing_credentials_never_looks_like_a_live_run(monkeypatch, tmp_path):
    monkeypatch.setenv("KINFOLD_AI_MODE", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    adapter = configured_provider()
    assert adapter.configured is False
    with TestClient(create_app(JsonRepository(tmp_path), adapter)) as client:
        assert client.get("/health").json()["providers"]["gemini"] is False
        client.post("/api/cases/demo", json={})
        result = client.post("/api/cases/demo-case/investigate", json={}).json()
        assert result["case"]["mode"] == "demo"
        assert result["metrics"]["documents_processed"] == 10
        assert result["audit"][-1]["action"] == "provider_unavailable"


def test_provider_annotations_do_not_change_deterministic_candidates(snapshot, tmp_path):
    class OfflineProvider:
        name, configured = "gemini", True

        def extract(self, current, _question):
            return validated_observations({"observations": [observation()]}, current, "gemini")[0], ["Offline transport test; not a real service run."]

    with TestClient(create_app(JsonRepository(tmp_path), OfflineProvider())) as client:
        client.post("/api/cases/demo", json={})
        result = client.post("/api/cases/demo-case/investigate", json={}).json()
        assert result["candidates"] == snapshot["candidates"]
        assert result["findings"][-1]["provider"] == "gemini"
        assert result["audit"][-1]["action"] == "provider_success"


def test_deepagents_compiles_restricted_real_google_harness_without_network(snapshot):
    pytest.importorskip("deepagents")
    from langchain_google_genai import ChatGoogleGenerativeAI
    from backend.providers import build_deep_agent
    model = ChatGoogleGenerativeAI(model="explicit-offline-test-model", api_key="offline-not-a-real-key")
    agent, _ = build_deep_agent(model, snapshot, [])
    tools = set(agent.nodes["tools"].bound.tools_by_name)
    assert tools == {"read_file", "plan_research", "retrieve_records", "extract_observations", "check_evidence"}
    assert not tools & {"execute", "task", "write_file", "edit_file", "delete", "glob", "grep"}


def test_deepagents_executes_plan_retrieve_extract_check_with_scripted_model(snapshot):
    pytest.importorskip("deepagents")
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage
    from backend.providers import build_deep_agent

    class ScriptedModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    def call(name, args, n):
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{n}", "type": "tool_call"}])

    model = ScriptedModel(responses=[call("read_file", {"file_path": "C:/private"}, 0), call("plan_research", {"steps": ["Retrieve source", "Extract cited observation", "Check constraints"]}, 1), call("retrieve_records", {"document_ids": ["d05"]}, 2), call("extract_observations", {"observations": [observation()]}, 3), call("check_evidence", {}, 4), AIMessage(content="Source-cited annotation ready for human review.")])
    trace = []
    agent, accepted = build_deep_agent(model, snapshot, trace)
    result = agent.invoke({"messages": [{"role": "user", "content": "Review sources."}]}, config={"recursion_limit": 24})
    assert trace == ["plan_research", "retrieve_records", "extract_observations", "check_evidence"]
    assert len(accepted) == 1
    assert any("not authorized" in str(m.content) for m in result["messages"])
    assert accepted[0]["citations"][0]["document_id"] == "d05"


def test_mongo_repository_uses_database_contract_and_sanitizes_connection_errors():
    class Collection:
        records = {}

        def replace_one(self, query, record, upsert=False):
            assert upsert
            self.records[query["_id"]] = deepcopy(record)

        def find_one(self, query):
            return deepcopy(self.records.get(query["_id"]))

        def find(self, *_args):
            return list(self.records.values())

    collection = Collection()

    class DB:
        def __getitem__(self, _key):
            return collection

    class Client:
        admin = SimpleNamespace(command=lambda command: {"ok": 1})

        def __getitem__(self, _key):
            return DB()

    repo = MongoRepository("not-used-in-offline-test", client=Client())
    repo.reset_demo()
    assert repo.get("demo-case")["case"]["synthetic"] is True
    assert "_id" not in repo.get("demo-case")
    assert len(repo.list()) == 1
    with pytest.raises(KeyError):
        repo.get("missing")
    class BadClient:
        @property
        def admin(self):
            raise ValueError("sensitive connection details")
    with pytest.raises(RuntimeError, match="MongoDB connection failed") as error:
        MongoRepository("mongodb://secret-user:secret-pass@invalid", client=BadClient())
    assert "secret-pass" not in str(error.value)
