"""Lead timeline: anchor research states on Solana devnet through the existing CLI.

Signing, broadcasting and on-chain checks all stay in `blockchain/anchor.mjs`. This module only writes the
manifest to a temporary file, runs that script, and reads its receipt. An anchor is stored only after the
script reports a *confirmed* transaction whose Memo it checked on-chain. Anchors live in `state["anchors"]`,
outside the evidence manifest, so a digest never covers its own anchor.

An anchor proves that this exact state existed, unchanged, by that time. It does not prove the records are true.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "blockchain" / "anchor.mjs"
LIMIT_NOTE = "Proves this exact state existed by this time, unchanged; it does not prove the records are true."
SETUP_HELP = ("Solana anchoring is not configured. Create a devnet-only keypair outside the repository "
              "(solana-keygen new --outfile <path>), fund it (solana airdrop 1 --url devnet --keypair <path>), "
              "set KINFOLD_SOLANA_KEYPAIR=<absolute path> in .env, and restart the API.")


class AnchorError(Exception):
    def __init__(self, status, detail):
        super().__init__(detail)
        self.status, self.detail = status, detail


def keypair_path():
    """The configured devnet keypair: an absolute path to an existing file outside the repository."""
    raw = os.getenv("KINFOLD_SOLANA_KEYPAIR", "").strip()
    if not raw:
        raise AnchorError(409, SETUP_HELP)
    path = Path(raw)
    if not path.is_absolute():
        raise AnchorError(409, "KINFOLD_SOLANA_KEYPAIR must be an absolute path.")
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise AnchorError(409, "Refusing a keypair inside the repository. Move it outside the project folder.")
    if not resolved.is_file():
        raise AnchorError(409, "KINFOLD_SOLANA_KEYPAIR does not point to an existing file.")
    return resolved


def run_node(args, timeout=150):
    """Run blockchain/anchor.mjs. Tests replace this function; it is the only place a subprocess starts."""
    node = os.getenv("KINFOLD_NODE", "node")
    return subprocess.run([node, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def _failure(proc):
    # anchor.mjs prints only its own error message on failure; keep it short and never echo arguments.
    message = (proc.stderr or proc.stdout or "").strip().splitlines()
    return message[-1][:300] if message else f"exit code {proc.returncode}"


def send(envelope):
    """Anchor one manifest envelope. Returns the confirmed receipt from anchor.mjs."""
    keypair = keypair_path()
    with tempfile.TemporaryDirectory(prefix="kinfold-anchor-") as tmp:
        manifest_file, receipt_file = Path(tmp) / "manifest.json", Path(tmp) / "receipt.json"
        manifest_file.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf8")
        try:
            proc = run_node(["--manifest", str(manifest_file), "--send", "--keypair", str(keypair), "--out", str(receipt_file)])
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AnchorError(502, f"Could not run the anchor script ({type(exc).__name__}). Nothing is claimed on-chain.") from None
        receipt = json.loads(receipt_file.read_text(encoding="utf8")) if receipt_file.exists() else {}
    if proc.returncode != 0 or receipt.get("status") != "confirmed":
        detail = f"Anchoring did not complete: {_failure(proc)}."
        if receipt.get("transaction"):
            detail += f" A transaction was submitted ({receipt['transaction']}) but not confirmed; check it on Solana Explorer before retrying."
        raise AnchorError(502, detail + " Nothing is claimed on-chain.")
    if receipt.get("digest") != envelope["digest"] or receipt.get("network") != "solana-devnet":
        raise AnchorError(502, "The anchor receipt does not match this manifest. Nothing is claimed on-chain.")
    return receipt


def verify(anchor):
    """Re-check a stored anchor against the chain with anchor.mjs --verify."""
    receipt = {k: anchor[k] for k in ("network", "digest", "memo", "transaction", "signer")}
    with tempfile.TemporaryDirectory(prefix="kinfold-verify-") as tmp:
        manifest_file, receipt_file = Path(tmp) / "manifest.json", Path(tmp) / "receipt.json"
        manifest_file.write_text(json.dumps(anchor["envelope"], ensure_ascii=False), encoding="utf8")
        receipt_file.write_text(json.dumps(receipt), encoding="utf8")
        try:
            proc = run_node(["--manifest", str(manifest_file), "--verify", str(receipt_file)], timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"Could not run the verifier ({type(exc).__name__})."
    if proc.returncode != 0:
        return False, _failure(proc)
    try:
        return json.loads(proc.stdout).get("status") == "verified_on_chain", "Transaction found on devnet with the expected Kinfold memo."
    except json.JSONDecodeError:
        return False, "Verifier output was not understood."


def lead_states(snapshot):
    return {c["person_id"]: c["status"] for c in snapshot["candidates"]}


def changes_since(previous, snapshot):
    """Plain-language differences from the previous anchor: lead status changes and records added."""
    if previous is None:
        return ["First anchor for this case."]
    names = {p["id"]: p["name"] for p in snapshot["people"]}
    out = []
    before, now = previous["leads"], lead_states(snapshot)
    for pid in sorted(set(before) | set(now), key=lambda i: names.get(i, i)):
        if before.get(pid) != now.get(pid):
            name = names.get(pid, pid)
            out.append(f"{name}: new lead ({now[pid]})" if pid not in before else f"{name}: {before[pid]} → {now.get(pid, 'removed')}")
    added = len(snapshot["documents"]) - previous["documents"]
    if added:
        out.append(f"{added} record(s) {'added' if added > 0 else 'removed'}")
    return out or ["No lead or record changes since the previous anchor."]


def record(envelope, receipt, snapshot, previous):
    names = {p["id"]: p["name"] for p in snapshot["people"]}
    return {"number": (previous["number"] + 1) if previous else 1, "digest": envelope["digest"], "version": envelope["version"],
            "network": "solana-devnet", "memo": receipt["memo"], "transaction": receipt["transaction"], "signer": receipt["signer"],
            "slot": receipt.get("slot"), "explorer": f"https://explorer.solana.com/tx/{receipt['transaction']}?cluster=devnet",
            "anchored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "leads": lead_states(snapshot), "lead_names": {pid: names.get(pid, pid) for pid in lead_states(snapshot)},
            "documents": len(snapshot["documents"]), "changes": changes_since(previous, snapshot), "envelope": envelope}


def public(anchor, current_digest):
    """Anchor as shown in snapshots: without the stored manifest copy, plus whether it matches the current state."""
    view = {k: v for k, v in anchor.items() if k != "envelope"}
    view["matches_current"] = anchor["digest"] == current_digest
    view["limits"] = LIMIT_NOTE
    return view
