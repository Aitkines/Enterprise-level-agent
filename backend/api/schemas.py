from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    payload: dict[str, Any] | None = None


class SessionSummary(BaseModel):
    session_id: str
    title: str
    updated_at: str | None = None
    filename: str | None = None


class SessionDetail(BaseModel):
    session: SessionSummary
    messages: list[ChatMessage]
    active_target: str | None = None
    active_targets: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    active_target: str | None = None
    active_targets: list[str] = Field(default_factory=list)
    session_id: str | None = None
    persist: bool = True


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    payload: dict[str, Any]
    active_target: str | None = None
    active_targets: list[str] = Field(default_factory=list)
    detected_targets: list[str] = Field(default_factory=list)
    messages: list[ChatMessage] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    seed_title: str | None = None


class SessionRenameRequest(BaseModel):
    title: str


class FinancialResponse(BaseModel):
    target: str
    symbol: str | None = None
    has_data: bool
    source: str | None = None
    unit_hint: str | None = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class ComparisonResponse(BaseModel):
    symbol: str
    snapshots: list[dict[str, Any]] = Field(default_factory=list)
    chart_specs: list[dict[str, Any]] = Field(default_factory=list)
    track_template: dict[str, Any] | None = None
    data_quality: dict[str, Any] = Field(default_factory=dict)
    scoring: dict[str, Any] = Field(default_factory=dict)


class ReportRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    active_target: str | None = None


class ReportResponse(BaseModel):
    html: str
