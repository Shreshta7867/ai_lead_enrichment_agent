from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LeadershipEntry(BaseModel):
    name: str | None = None
    role: str | None = None
    linkedin_url: str | None = None


class CompanyResult(BaseModel):
    domain: str
    company_overview: str = ""
    target_audience: str = ""
    contact_points: list[str] = Field(default_factory=list)
    leadership: list[LeadershipEntry] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    status: Literal["success", "partial", "failed"] = "success"
    error: str | None = None


class PageContent(BaseModel):
    url: str
    title: str
    text: str
