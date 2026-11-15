from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    quote: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_line < self.start_line:
            raise ValueError("Citation end precedes start")
        return self


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["birth", "death", "alive", "parent", "spouse", "sibling", "dna_match", "birth_range", "case_death", "case_region"]
    subject: str
    object_id: str | None = None
    value: str | int | None = None
    location: str | None = None
    citation: Citation


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(default="", max_length=2000)
    max_steps: int = Field(default=3, ge=1, le=5)


class UploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=100000)

    @model_validator(mode="after")
    def meaningful(self):
        if not self.name.strip() or not self.text.strip():
            raise ValueError("Record name and text cannot be blank")
        self.text.encode("utf8")  # reject malformed Unicode before hashing or persistence
        # Normalize Windows/old-Mac line endings. Line spans count "\n" lines, and recorded AI replays are
        # matched on the exact text hash; a CRLF checkout (git core.autocrlf) would otherwise miss them.
        self.text = self.text.replace("\r\n", "\n").replace("\r", "\n")
        return self


class PhotoUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    image_base64: str = Field(min_length=8, max_length=5_600_000)
    capture: Literal["webcam", "phone", "file"] = "file"


class PhotoConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lines: list[str] = Field(max_length=80)


class VerifyRequest(BaseModel):
    digest: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


def validate_citation(citation: Citation | dict, documents: list[dict]) -> bool:
    try:
        c = citation if isinstance(citation, Citation) else Citation.model_validate(citation)
        document = next(d for d in documents if d["id"] == c.document_id)
        lines = document["text"].split("\n")
        return c.end_line <= len(lines) and c.quote in "\n".join(lines[c.start_line - 1:c.end_line])
    except (ValueError, StopIteration, KeyError):
        return False
