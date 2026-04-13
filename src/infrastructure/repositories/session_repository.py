from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from threading import Lock, RLock
from typing import Any


class SessionRepository:
    _registry_lock = Lock()
    _path_locks: dict[str, RLock] = {}

    def __init__(self, data_dir: str = "data/sessions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _lock_for_path(cls, path: Path) -> RLock:
        key = str(path.resolve())
        with cls._registry_lock:
            lock = cls._path_locks.get(key)
            if lock is None:
                lock = RLock()
                cls._path_locks[key] = lock
            return lock

    def _normalize_filename(self, session_id: str) -> str:
        return session_id if session_id.endswith(".json") else f"{session_id}.json"

    def _path_for(self, session_id: str) -> Path:
        return self.data_dir / self._normalize_filename(session_id)

    def _read_json_unlocked(self, path: Path) -> list[dict[str, Any]] | None:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json_unlocked(self, path: Path, payload: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=str(path.parent),
                delete=False,
                suffix=".tmp",
            ) as temp_file:
                json.dump(payload, temp_file, ensure_ascii=False, indent=2)
                temp_path = temp_file.name
            os.replace(temp_path, path)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def save_messages(self, session_id: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        path = self._path_for(session_id)
        lock = self._lock_for_path(path)
        with lock:
            snapshot = list(messages)
            self._write_json_unlocked(path, snapshot)
            return snapshot

    def append_messages(self, session_id: str, new_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        path = self._path_for(session_id)
        lock = self._lock_for_path(path)
        with lock:
            existing_messages = self._read_json_unlocked(path) or []
            merged_messages = list(existing_messages)
            merged_messages.extend(list(new_messages))
            self._write_json_unlocked(path, merged_messages)
            return merged_messages

    def load_messages_if_exists(self, filename: str) -> list[dict[str, Any]] | None:
        path = self._path_for(filename)
        lock = self._lock_for_path(path)
        with lock:
            payload = self._read_json_unlocked(path)
            return list(payload) if payload is not None else None

    def load_messages(self, filename: str) -> list[dict[str, Any]]:
        return self.load_messages_if_exists(filename) or []

    def list_history_files(self, limit: int = 20) -> list[str]:
        files = [path for path in self.data_dir.iterdir() if path.suffix == ".json"]
        files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        return [path.name for path in files[:limit]]

    def list_session_previews(self, limit: int = 20) -> list[dict[str, Any]]:
        previews: list[dict[str, Any]] = []
        for filename in self.list_history_files(limit):
            path = self._path_for(filename)
            lock = self._lock_for_path(path)
            with lock:
                messages = self._read_json_unlocked(path) or []
                mtime = path.stat().st_mtime if path.exists() else datetime.now().timestamp()

            dt = datetime.fromtimestamp(mtime)
            title = "New Chat"
            for msg in messages:
                if msg.get("role") != "user":
                    continue
                content = str(msg.get("content") or "").strip()
                if not content or set(content) == {"?"}:
                    continue
                title = content[:15]
                break

            previews.append(
                {
                    "session_id": filename.replace(".json", ""),
                    "title": title,
                    "updated_at": dt.strftime("%Y-%m-%d %H:%M"),
                    "filename": filename,
                }
            )
        return previews

    def resolve_session_id(self, preferred_id: str) -> str:
        return preferred_id

    def delete_session(self, filename: str) -> None:
        path = self._path_for(filename)
        lock = self._lock_for_path(path)
        with lock:
            if path.exists():
                path.unlink()

    def rename_session(self, filename: str, new_title: str) -> str:
        return filename
