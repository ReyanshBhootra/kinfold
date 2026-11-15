from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from backend.engine import derive
from backend.gemini_schema import gemini_schema
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
        return SimpleNamespace(text=json.dumps({"observations": [observation()]}))

    adapter = GeminiProvider("offline-test", "explicit-model", SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    result, trace = adapter.extract(snapshot, "Compare birth years")
    assert len(result) == 1 and "structured extraction" in trace[0]
    assert calls[0]["config"].response_schema == gemini_schema(ObservationBatch)
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


# --- issue #8: live annotation replies failed strict validation as a whole -------------------------------------

def fake_gemini(reply_text):
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=reply_text)
    return GeminiProvider("offline-test", "explicit-model", SimpleNamespace(models=SimpleNamespace(generate_content=generate))), calls


def test_annotation_schema_never_sends_size_limits_gemini_rejects():
    """Regression (#8, live run on PR #17): gemini-3.5-flash answers 400 INVALID_ARGUMENT when the schema has
    minItems/maxItems. Limits are stated in the prompt and field descriptions and enforced per item locally."""
    from backend.providers import SYSTEM
    sent = json.dumps(gemini_schema(ObservationBatch))
    for keyword in ("minItems", "maxItems", "minLength", "maxLength"):
        assert keyword not in sent
    item = gemini_schema(ObservationBatch)["properties"]["observations"]["items"]["properties"]
    assert "known_people" in item["person_ids"]["description"] and "160" in item["title"]["description"]
    assert "At most 12 observations" in SYSTEM and "1 to 4 citations" in SYSTEM


def test_one_bad_observation_no_longer_discards_the_valid_ones(snapshot):
    pytest.importorskip("google.genai")
    good = observation()
    uncited = {**observation(), "title": "No citation", "citations": []}
    too_long = {**observation(), "title": "x" * 161}
    extra_field = {**observation(), "confidence": "high"}
    adapter, _ = fake_gemini(json.dumps({"observations": [good, uncited, too_long, extra_field]}))
    findings, trace = adapter.extract(snapshot, "")
    assert len(findings) == 1 and findings[0]["title"] == "Model suggestion · " + good["title"]
    assert "rejected 3 on schema" in trace[0]
    assert "observations[1].citations: too_short" in trace[0] and "observations[2].title: string_too_long" in trace[0]
    assert "observations[3].confidence: extra_forbidden" in trace[0]
    assert "x" * 20 not in trace[0] and "high" not in trace[0]  # locations and types only, never reply content


def test_items_past_the_limit_are_rejected_not_fatal(snapshot):
    pytest.importorskip("google.genai")
    adapter, _ = fake_gemini(json.dumps({"observations": [observation()] * 14}))
    findings, trace = adapter.extract(snapshot, "")
    assert len(findings) == 1  # 12 parsed; exact repeats collapse to one finding (one stable id)
    assert "rejected 2 on schema" in trace[0] and "over the 12-item limit" in trace[0]


@pytest.mark.parametrize("reply, message", [
    ('{"observations": [{"title": "cut off', "not valid JSON"),
    ('[{"title": "x"}]', "expected {observations"),
    ('{"observations": [], "notes": "x"}', "expected {observations"),
])
def test_malformed_replies_still_fail_the_whole_call(snapshot, reply, message):
    pytest.importorskip("google.genai")
    adapter, _ = fake_gemini(reply)
    with pytest.raises(ProviderError, match=message):
        adapter.extract(snapshot, "")


def test_all_invalid_reply_reports_safe_diagnostics_in_the_audit(tmp_path):
    pytest.importorskip("google.genai")
    secret_text = "SECRET-REPLY-TEXT"
    adapter, _ = fake_gemini(json.dumps({"observations": [{**observation(), "title": secret_text * 20, "citations": []}]}))
    with TestClient(create_app(JsonRepository(tmp_path), adapter, extractor=None)) as client:
        client.post("/api/cases/demo", json={})
        result = client.post("/api/cases/demo-case/investigate", json={}).json()
    entry = result["audit"][-1]
    assert entry["action"] == "provider_unavailable" and result["case"]["mode"] == "demo"
    assert "observations[0].title: string_too_long" in entry["description"] and "observations[0].citations: too_short" in entry["description"]
    assert secret_text not in entry["description"]
