from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


class DouyinLinkStore:
    """负责持久化保存抖音链接到本地 JSON 文件。"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save_link(self, raw_text: str) -> None:
        normalized_url = self.extract_douyin_url(raw_text)
        if not normalized_url:
            return

        records = self._load_records()
        records.append(
            {
                "raw_text": raw_text.strip(),
                "url": normalized_url,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self._write_records(records)

    def get_links(self) -> list[dict]:
        records = self._load_records()
        normalized_records = []
        for index, item in enumerate(records):
            if not isinstance(item, dict):
                continue
            source_text = item.get("raw_text")
            if not isinstance(source_text, str) or not source_text.strip():
                source_text = item.get("url")
            if not isinstance(source_text, str) or not source_text.strip():
                continue
            url = self.extract_douyin_url(source_text)
            if not url:
                continue
            display_text = self.build_display_text(source_text, url)
            created_at = item.get("created_at", "")
            normalized_records.append(
                {
                    "index": index,
                    "url": url,
                    "display_text": display_text,
                    "created_at": created_at if isinstance(created_at, str) else "",
                }
            )
        return normalized_records

    def delete_link(self, index: int) -> bool:
        records = self._load_records()
        if index < 0 or index >= len(records):
            return False
        del records[index]
        self._write_records(records)
        return True

    def _load_records(self) -> list[dict]:
        if not self.file_path.exists():
            return []

        try:
            content = self.file_path.read_text(encoding="utf-8").strip()
            if not content:
                return []
            data = json.loads(content)
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

    @staticmethod
    def extract_douyin_url(raw_text: str) -> str:
        text = raw_text.strip()
        if not text:
            return ""

        match = re.search(r"https?://[^\s]+", text)
        candidate = match.group(0) if match else text

        # 清除常见收尾符号（包含 markdown 反引号）
        candidate = candidate.rstrip("`'\"，。,.!！；;）)")
        if "douyin.com" not in candidate:
            return ""
        return candidate

    @staticmethod
    def build_display_text(raw_text: str, url: str) -> str:
        text = raw_text.strip()
        if not text:
            return url

        # 去掉正文中的 URL，仅保留描述文本
        text_without_url = text.replace(url, " ")
        text_without_url = re.sub(r"\s+", " ", text_without_url).strip()
        if text_without_url:
            return text_without_url
        return url
