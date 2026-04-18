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
        now = datetime.now().isoformat(timespec="seconds")
        new_record = {
            "raw_input": raw_input,
            "short_url": short_url,
            "resolved_url": resolved_url,
            "extracted_text": extracted_text,
            "summary": summary,
            "created_at": now,
            "updated_at": now,
        }

        updated = False
        for index, item in enumerate(records):
            if not isinstance(item, dict):
                continue
            if item.get("short_url") == short_url:
                # 以短链为唯一键，保持与已保存链接一一对应
                new_record["created_at"] = item.get("created_at", now)
                records[index] = new_record
                updated = True
                break

        if not updated:
            records.append(new_record)
        self._write_records(records)

    def get_summary_by_short_url(self, short_url: str) -> dict | None:
        for item in self._load_records():
            if not isinstance(item, dict):
                continue
            if item.get("short_url") == short_url:
                return item
        return None

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
