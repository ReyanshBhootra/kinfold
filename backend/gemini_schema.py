"""Gemini-compatible response schemas.

Gemini's `response_schema` accepts an OpenAPI subset. Passing a strict Pydantic model directly
sends `additionalProperties` (from extra="forbid"), `$ref`/`$defs` and `anyOf` nulls, which the
API rejects with 400 INVALID_ARGUMENT. We send this simplified schema to steer the model, then
validate the reply with the original strict Pydantic model, so nothing is loosened on our side.
"""
from pydantic import BaseModel

_KEEP = {"type", "required", "enum", "description", "nullable", "minimum", "maximum", "format"}
# Size limits. Gemini's Schema supports them (google.genai types.Schema: min_items/max_items/min_length/max_length).
# Without them the model is never told our limits, and one oversized item fails strict validation.
_LIMITS = {"minItems", "maxItems", "minLength", "maxLength"}


def gemini_schema(model: type[BaseModel], limits: bool = False) -> dict:
    keep = _KEEP | _LIMITS if limits else _KEEP
    schema = model.model_json_schema()
    defs = schema.get("$defs", {})

    def walk(node):
        if "$ref" in node:
            return walk(defs[node["$ref"].split("/")[-1]])
        if "anyOf" in node:  # Optional[X] -> X with nullable
            options = [o for o in node["anyOf"] if o.get("type") != "null"]
            out = walk(options[0])
            if len(options) < len(node["anyOf"]):
                out["nullable"] = True
            return out
        out = {k: v for k, v in node.items() if k in keep}
        if "properties" in node:
            out["properties"] = {name: walk(sub) for name, sub in node["properties"].items()}
        if "items" in node:
            out["items"] = walk(node["items"])
        return out

    return walk(schema)


def parse(response, model: type[BaseModel]):
    """Validate a Gemini reply strictly, whatever form the SDK returned it in."""
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, model):
        return parsed
    return model.model_validate_json(response.text)


def retry_options(types, attempts=4):
    """Retry overloads (429/503/504) with exponential backoff; the SDK does the waiting."""
    return types.HttpRetryOptions(attempts=attempts, initial_delay=2.0, max_delay=20.0, http_status_codes=[408, 429, 500, 502, 503, 504])
