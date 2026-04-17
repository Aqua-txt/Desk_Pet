from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class SummaryStore:
    """持久化保存视频总结结果。"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def add_summary(
        self,
        raw_input: str,
        short_url: str,
        resolved_url: str,
        extracted_text: str,
        summary: str,
    ) -> None:
        records = self._load_records()
        records.append(
            {
                "raw_input": raw_input,
                "short_url": short_url,
                "resolved_url": resolved_url,
                "extracted_text": extracted_text,
                "summary": summary,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self._write_records(records)

    def _load_records(self) -> list[dict]:
        if not self.file_path.exists():
            return []
        try:
            text = self.file_path.read_text(encoding="utf-8").strip()
            if not text:
                return []
            data = json.loads(text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            return []
        return []

    def _write_records(self, records: list[dict]) -> None:
        self.file_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
