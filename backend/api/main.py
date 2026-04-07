from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import pandas as pd
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.infrastructure.utils.file_processor import FileProcessor

from src.application.services.chat_service import ChatService
from src.application.services.company_service import CompanyService
from src.application.services.comparison_service import ComparisonService
from src.application.services.dashboard_service import DashboardService
from src.application.services.data_quality_service import DataQualityService
from src.application.services.financial_service import FinancialService
from src.application.services.report_service import ReportService
from src.application.services.track_scoring_service import TrackScoringService
from src.infrastructure.repositories.session_repository import SessionRepository
from src.shared.response_payload import build_response_payload_from_text
from src.shared.session_title import (
    build_default_session_id,
    extract_session_title,
    normalize_manual_title,
)

from .schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ComparisonResponse,
    FinancialResponse,
    ReportRequest,
    ReportResponse,
    SessionCreateRequest,
    SessionDetail,
    SessionRenameRequest,
    SessionSummary,
)


app = FastAPI(
    title="Radiant Surface API",
    version="0.1.0",
    description="React frontend API layer for the existing Python service stack.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


chat_service = ChatService()
company_service = CompanyService()
comparison_service = ComparisonService()
dashboard_service = DashboardService()
data_quality_service = DataQualityService()
financial_service = FinancialService()
report_service = ReportService()
track_scoring_service = TrackScoringService()
session_repository = SessionRepository()
SESSION_META_PATH = ROOT_DIR / "data" / "session_meta.json"


def _sanitize_session_id(value: str) -> str:
    normalized = re.sub(r"[^\w\-]+", "-", value.strip().lower()).strip("-")
    return normalized[:48] or "session"


def _build_unique_session_id(seed: str | None) -> str:
    base = _sanitize_session_id(build_default_session_id(seed or "session"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{timestamp}"


def _session_filename(session_id: str) -> str:
    return session_id if session_id.endswith(".json") else f"{session_id}.json"


def _load_session_meta() -> dict[str, dict[str, Any]]:
    if not SESSION_META_PATH.exists():
        return {}
    try:
        return json.loads(SESSION_META_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_session_meta(meta: dict[str, dict[str, Any]]) -> None:
    SESSION_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_META_PATH.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _get_custom_title(session_id: str) -> str | None:
    return _load_session_meta().get(session_id, {}).get("title")


def _set_custom_title(session_id: str, title: str) -> None:
    meta = _load_session_meta()
    meta.setdefault(session_id, {})
    meta[session_id]["title"] = title
    _save_session_meta(meta)


def _delete_session_meta(session_id: str) -> None:
    meta = _load_session_meta()
    if session_id in meta:
        meta.pop(session_id, None)
        _save_session_meta(meta)


def _safe_value(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        try:
            converted = value.item()
            if isinstance(converted, float) and math.isnan(converted):
                return None
            return converted
        except Exception:
            return str(value)
    return value


def _records_from_dataframe(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    records: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        records.append({str(key): _safe_value(value) for key, value in row.items()})
    return records


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return _records_from_dataframe(value)
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return _safe_value(value)


def _summary_from_messages(session_id: str, messages: list[dict[str, Any]]) -> SessionSummary:
    title = _get_custom_title(session_id) or (extract_session_title(messages) if messages else "新对话")
    return SessionSummary(
        session_id=session_id,
        title=title or "新对话",
        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        filename=_session_filename(session_id),
    )


def _load_session_messages(session_id: str) -> list[dict[str, Any]]:
    filename = _session_filename(session_id)
    messages = session_repository.load_messages_if_exists(filename)
    if messages is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return messages


def _persist_messages(session_id: str, messages: list[dict[str, Any]]) -> None:
    session_repository.save_messages(_session_filename(session_id), messages)


def _normalize_targets(prompt: str, active_target: str | None, active_targets: list[str]) -> tuple[list[str], str | None, list[str]]:
    detected_targets = company_service.identify_target_companies(prompt)
    if detected_targets:
        return detected_targets, detected_targets[0], detected_targets
    if active_target:
        return [], active_target, active_targets or [active_target]
    return [], None, []


def _history_to_messages(chat_history: list[ChatMessage]) -> list[dict[str, Any]]:
    return [message.model_dump() for message in chat_history]


def _compose_chat_messages(existing_messages: list[dict[str, Any]], prompt: str, reply: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages = list(existing_messages)
    messages.append({"role": "user", "content": prompt})
    messages.append({"role": "assistant", "content": reply, "payload": payload})
    return messages


def _run_chat_completion(request: ChatRequest) -> tuple[str, dict[str, Any], str | None, list[str], list[str], list[dict[str, Any]]]:
    if request.session_id:
        existing_messages = _load_session_messages(request.session_id)
    else:
        existing_messages = _history_to_messages(request.chat_history)

    detected_targets, active_target, active_targets = _normalize_targets(
        request.prompt,
        request.active_target,
        request.active_targets,
    )

    stream = chat_service.run_query_stream(
        request.prompt,
        chat_history=existing_messages,
        active_target=active_target,
        active_targets=active_targets,
    )
    reply = "".join(chunk for chunk in stream)
    payload = build_response_payload_from_text(reply, source="chat_service")
    return reply, payload, active_target, active_targets, detected_targets, existing_messages


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "app": "radiant-surface-api",
    }


@app.get("/api/dashboard/overview")
def get_dashboard_overview() -> dict[str, Any]:
    return _to_jsonable(dashboard_service.get_data_overview())


@app.get("/api/dashboard/system-status")
def get_system_status(msg_count: int = 0) -> dict[str, Any]:
    return _to_jsonable(dashboard_service.get_system_status(msg_count=msg_count))


@app.get("/api/sessions", response_model=list[SessionSummary])
def list_sessions(limit: int = 20) -> list[SessionSummary]:
    previews = session_repository.list_session_previews(limit=limit)
    session_meta = _load_session_meta()
    summaries: list[SessionSummary] = []
    for preview in previews:
        title_override = session_meta.get(preview["session_id"], {}).get("title")
        summaries.append(SessionSummary(**{**preview, "title": title_override or preview["title"]}))
    return summaries


@app.post("/api/sessions", response_model=SessionDetail)
def create_session(request: SessionCreateRequest) -> SessionDetail:
    seed_title = normalize_manual_title(request.seed_title or "") or "新对话"
    session_id = _build_unique_session_id(seed_title)
    messages: list[dict[str, Any]] = []
    _persist_messages(session_id, messages)
    _set_custom_title(session_id, seed_title)
    summary = _summary_from_messages(session_id, messages)
    return SessionDetail(session=summary, messages=[])


@app.get("/api/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str) -> SessionDetail:
    messages = _load_session_messages(session_id)
    summary = _summary_from_messages(session_id, messages)
    return SessionDetail(
        session=summary,
        messages=[ChatMessage(**message) for message in messages],
    )


@app.put("/api/sessions/{session_id}", response_model=SessionDetail)
def rename_session(session_id: str, request: SessionRenameRequest) -> SessionDetail:
    messages = _load_session_messages(session_id)
    _set_custom_title(session_id, normalize_manual_title(request.title) or "新对话")
    summary = _summary_from_messages(session_id, messages)
    return SessionDetail(
        session=summary,
        messages=[ChatMessage(**message) for message in messages],
    )


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, Any]:
    filename = _session_filename(session_id)
    session_repository.delete_session(filename)
    _delete_session_meta(session_id)
    return {"deleted": True, "session_id": session_id}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply, payload, active_target, active_targets, detected_targets, existing_messages = _run_chat_completion(request)

    session_id = request.session_id or _build_unique_session_id(
        extract_session_title([{"role": "user", "content": request.prompt}])
    )
    messages = _compose_chat_messages(existing_messages, request.prompt, reply, payload)
    if request.persist:
        _persist_messages(session_id, messages)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        payload=_to_jsonable(payload),
        active_target=active_target,
        active_targets=active_targets,
        detected_targets=detected_targets,
        messages=[ChatMessage(**message) for message in messages],
    )


@app.post("/api/chat/stream")
async def chat_stream(
    prompt: str = Form(...),
    session_id: str = Form(None),
    chat_history: str = Form("[]"),
    active_target: str = Form(None),
    active_targets: str = Form("[]"),
    persist: bool = Form(True),
    files: list[UploadFile] = File(None)
) -> StreamingResponse:
    # Parse JSON strings from Form
    try:
        history_list = json.loads(chat_history)
        history_objs = [ChatMessage(**m) for m in history_list]
        targets_list = json.loads(active_targets)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in form fields: {str(e)}")

    # Process Files
    uploaded_context = []
    if files:
        for file in files:
            content = await file.read()
            parsed_text = FileProcessor.process_file(file.filename, content)
            if parsed_text:
                uploaded_context.append(f"--- FILE: {file.filename} ---\n{parsed_text}\n")

    full_prompt = prompt
    if uploaded_context:
        context_str = "\n".join(uploaded_context)
        full_prompt = f"核心分析指令: {prompt}\n\n[以下是用户上传的私有文档数据，请优先基于此数据进行研判]:\n{context_str}"

    target_session_id = session_id or _build_unique_session_id(
        extract_session_title([{"role": "user", "content": prompt}])
    )
    existing_messages = _load_session_messages(target_session_id) if session_id else _history_to_messages(history_objs)
    
    detected_targets, norm_active_target, norm_active_targets = _normalize_targets(
        prompt,
        active_target,
        targets_list,
    )

    def event_stream() -> Iterable[str]:
        reply_parts: list[str] = []
        try:
            stream = chat_service.run_query_stream(
                full_prompt,
                chat_history=existing_messages,
                active_target=norm_active_target,
                active_targets=norm_active_targets,
            )
            for chunk in stream:
                reply_parts.append(chunk)
                data = {"type": "chunk", "content": chunk}
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            reply = "".join(reply_parts)
            payload = build_response_payload_from_text(reply, source="chat_service")
            messages = _compose_chat_messages(existing_messages, prompt, reply, payload)
            if persist:
                _persist_messages(target_session_id, messages)

            done_payload = {
                "type": "done",
                "session_id": target_session_id,
                "payload": _to_jsonable(payload),
                "reply": reply,
                "active_target": norm_active_target,
                "active_targets": norm_active_targets,
                "detected_targets": detected_targets,
                "messages": messages,
            }
            yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            import traceback
            traceback.print_exc()
            error_payload = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/financial/{target}", response_model=FinancialResponse)
def get_financials(target: str) -> FinancialResponse:
    financial_table = financial_service.get_financial_table(target)
    symbol_match = re.search(r"\d{6}", str(target))
    symbol = symbol_match.group(0) if symbol_match else None

    if financial_table is None or financial_table.is_empty():
        return FinancialResponse(
            target=target,
            symbol=symbol,
            has_data=False,
            error="No financial data available for the requested target.",
        )

    frame = financial_table.to_dataframe()
    return FinancialResponse(
        target=target,
        symbol=symbol,
        has_data=True,
        source=financial_table.source,
        unit_hint=financial_table.unit_hint,
        rows=_records_from_dataframe(frame),
    )


@app.get("/api/comparison/{symbol}", response_model=ComparisonResponse)
def get_comparison(symbol: str, limit: int = 10, max_metrics: int = 4) -> ComparisonResponse:
    snapshots = comparison_service.get_peer_snapshots_for_symbol(symbol, limit=limit)
    track_template = comparison_service.get_track_template_for_symbol(symbol)
    metric_keys = [metric.key for metric in track_template.metrics] if track_template else []
    metric_display_map = (
        {metric.key: metric.display_name for metric in track_template.metrics}
        if track_template
        else {}
    )
    quality_result = data_quality_service.build_track_data_quality(
        snapshots=snapshots,
        metric_keys=metric_keys,
        metric_display_map=metric_display_map,
    )
    scoring_result = track_scoring_service.score_snapshots(
        snapshots=snapshots,
        track_template=track_template,
    )
    chart_specs = comparison_service.build_track_chart_specs(
        symbol,
        limit=limit,
        max_metrics=max_metrics,
    )

    template_payload = None
    if track_template is not None:
        template_payload = {
            "track_name": track_template.track_name,
            "focus": track_template.focus,
            "metrics": [
                {
                    "key": metric.key,
                    "display_name": metric.display_name,
                    "is_positive": metric.is_positive,
                }
                for metric in track_template.metrics
            ],
        }

    return ComparisonResponse(
        symbol=symbol,
        snapshots=_to_jsonable(snapshots),
        chart_specs=_to_jsonable(chart_specs),
        track_template=template_payload,
        data_quality=_to_jsonable(quality_result),
        scoring=_to_jsonable(scoring_result),
    )


@app.post("/api/report", response_model=ReportResponse)
def build_report(request: ReportRequest) -> ReportResponse:
    html_bytes = report_service.build_html_report(
        messages=[message.model_dump() for message in request.messages],
        generated_at=datetime.now(),
        active_target=request.active_target,
    )
    html = html_bytes.decode("utf-8", errors="replace")
    return ReportResponse(html=html)
