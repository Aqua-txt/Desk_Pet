from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class PetGrowthStore:
    """持久化保存桌宠成长数据。"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict:
        if not self.file_path.exists():
            return self.default_state()
        try:
            content = self.file_path.read_text(encoding="utf-8").strip()
            if not content:
                return self.default_state()
            data = json.loads(content)
            if not isinstance(data, dict):
                return self.default_state()
            return self._normalize(data)
        except json.JSONDecodeError:
            return self.default_state()

    def save_state(self, state: dict) -> None:
        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.file_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def default_state() -> dict:
        return {
            "exp": 0,
            "streak_days": 0,
            "last_active_date": "",
            "corner_logs": [],
            "passion_tasks": [],
            "future_messages": [],
            "updated_at": "",
        }

    def _normalize(self, state: dict) -> dict:
        normalized = self.default_state()
        normalized["exp"] = max(0, int(state.get("exp", 0)))
        normalized["streak_days"] = max(0, int(state.get("streak_days", 0)))
        normalized["last_active_date"] = str(state.get("last_active_date", "") or "")
        normalized["updated_at"] = str(state.get("updated_at", "") or "")
        normalized["corner_logs"] = self._as_list(state.get("corner_logs"))
        normalized["passion_tasks"] = self._as_list(state.get("passion_tasks"))
        normalized["future_messages"] = self._as_list(state.get("future_messages"))
        return normalized

    @staticmethod
    def _as_list(value) -> list:
        if isinstance(value, list):
            return value
        return []
