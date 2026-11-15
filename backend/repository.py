from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import re
from threading import RLock
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent


# Who is acting, set per request from the X-Kinfold-Researcher header (backend/main.py). A self-declared
# display name for case handoff, not authentication: this local prototype has no sign-in.
current_actor = ContextVar("kinfold_actor", default=None)


def event(action, description):
    return {"id": "e-" + uuid4().hex[:12], "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "action": action, "description": description, "actor": current_actor.get()}


def demo_state():
    state = json.loads((ROOT / "data" / "demo_case.json").read_text(encoding="utf8"))
    state["audit"] = [event("case_loaded", "Loaded the disclosed synthetic Alder Creek fixture. No live AI or genetic inference was run.")]
    state["model_findings"] = []
    for document in state["documents"]:
        document["provenance"] = {"origin": "synthetic_fixture", "original_name": document["name"], "received_at": None,
                                  "text_sha256": hashlib.sha256(document["text"].encode("utf8")).hexdigest(), "authenticity": "Synthetic research fixture; no historical authenticity claimed"}
    return state


class JsonRepository:
    """Atomic local JSON persistence. One process; a reentrant lock guards read-modify-write."""
    def __init__(self, directory=None):
        self.directory = Path(directory or os.getenv("KINFOLD_DATA_DIR", ROOT / "data" / "runtime"))
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.kind = "json"

    def _path(self, case_id):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", case_id):
            raise KeyError(case_id)
        return self.directory / f"{case_id}.json"

    def list(self):
        with self.lock:
            return [json.loads(p.read_text(encoding="utf8"))["case"] for p in sorted(self.directory.glob("*.json"))]

    def get(self, case_id):
        with self.lock:
            path = self._path(case_id)
            if not path.exists():
                raise KeyError(case_id)
            return json.loads(path.read_text(encoding="utf8"))

    def put(self, state):
        with self.lock:
            destination = self._path(state["case"]["id"])
            temporary = destination.with_suffix(f".{uuid4().hex}.tmp")
            try:
                temporary.write_text(json.dumps(state, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    temporary.unlink()

    def reset_demo(self):
        with self.lock:
            state = demo_state()
            self.put(state)
            return deepcopy(state)


class MongoRepository:
    """Optional real MongoDB persistence. A configured connection must actually ping."""
    kind = "mongodb"

    def __init__(self, uri, database="kinfold", client=None):
        self.lock = RLock()
        try:
            if client is None:
                from pymongo import MongoClient
                client = MongoClient(uri, serverSelectionTimeoutMS=4000, connectTimeoutMS=4000, timeoutMS=8000)
            client.admin.command("ping")
            self.client = client
            self.collection = client[database]["cases"]
        except Exception:
            raise RuntimeError("MongoDB connection failed. Check server-side URI/network setup; no local fallback was silently selected.") from None

    def list(self):
        return [record["case"] for record in self.collection.find({}, {"case": 1})]

    def get(self, case_id):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", case_id):
            raise KeyError(case_id)
        result = self.collection.find_one({"_id": case_id})
        if result is None:
            raise KeyError(case_id)
        result.pop("_id", None)
        return result

    def put(self, state):
        self.collection.replace_one({"_id": state["case"]["id"]}, {"_id": state["case"]["id"], **deepcopy(state)}, upsert=True)

    def reset_demo(self):
        with self.lock:
            state = demo_state(); self.put(state); return state


def configured_repository():
    mode = os.getenv("KINFOLD_STORAGE", "json").lower()
    if mode == "json":
        return JsonRepository()
    if mode != "mongodb" or not os.getenv("MONGODB_URI"):
        raise RuntimeError("Set KINFOLD_STORAGE=json, or mongodb with a server-side MONGODB_URI.")
    return MongoRepository(os.environ["MONGODB_URI"], os.getenv("MONGODB_DATABASE", "kinfold"))
