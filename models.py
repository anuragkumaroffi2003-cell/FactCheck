from pydantic import BaseModel, Field
from typing import Literal


class Claim(BaseModel):
    id: int
    text: str
    context: str


class Evidence(BaseModel):
    text: str
    url: str
    published_date: str | None = None


class Verdict(BaseModel):
    claim: Claim

    status: Literal[
        "Verified",
        "Inaccurate",
        "False",
        "Unverifiable"
    ]

    corrected_fact: str | None = None

    explanation: str

    evidence_used: list[Evidence] = Field(
        default_factory=list
    )

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    source_agreement: str = "0/0"
