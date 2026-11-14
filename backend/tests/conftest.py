"""Keep the test suite offline and deterministic regardless of a developer's local .env.

backend.main calls load_dotenv() on import. load_dotenv never overrides variables that are
already set, so pinning them here (before any test module imports the app) stops tests from
making live Gemini/MongoDB calls or writing to the real data/ai_cache.
"""
import os
import tempfile

os.environ["KINFOLD_AI_MODE"] = "demo"
os.environ["KINFOLD_STORAGE"] = "json"
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["MONGODB_URI"] = ""
os.environ["KINFOLD_AI_CACHE"] = tempfile.mkdtemp(prefix="kinfold-test-cache-")
