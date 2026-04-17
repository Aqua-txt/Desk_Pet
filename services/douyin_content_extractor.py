from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.request


class DouyinContentExtractor:
    """
    从视频页面抽取可用于总结的文本信息。

    说明：
    - 抖音页面常有风控，无法保证每次都拿到完整内容；
    - 这里优先提取标题/描述/标签/疑似字幕字段，作为 ASR/OCR 的近似文本输入。
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )

    def extract(self, resolved_url: str, raw_input_text: str = "", video_id: str = "") -> str:
        chunks = []
        # 第一优先级：用户粘贴的分享文案本身通常包含标题/话题，可直接提供视频主题线索
        chunks.extend(self._extract_text_from_raw_input(raw_input_text, resolved_url))

        # 第二优先级：若拿到视频 ID，尝试公开详情接口提取 desc/author/tag
        if video_id:
            chunks.extend(self._extract_text_from_item_api(video_id))

        # 第三优先级：页面 HTML 兜底提取
        html_text = self._fetch_html(resolved_url)
        if html_text:
            chunks.extend(self._extract_meta_text(html_text))
            chunks.extend(self._extract_json_text(html_text))

        merged = self._merge_chunks(chunks)
        if not merged:
            return (
                "未能自动提取到足够视频文本信息。"
                "请基于以下链接做结构化摘要并标注信息不足："
                f"{resolved_url}"
            )
        return merged

    def _fetch_html(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": self.USER_AGENT},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                raw_bytes = response.read()
            return raw_bytes.decode("utf-8", errors="ignore")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            return ""

    def _extract_text_from_raw_input(self, raw_input_text: str, resolved_url: str) -> list[str]:
        if not raw_input_text.strip():
            return []

        text = raw_input_text.strip()
        text = text.replace(resolved_url, " ")
        text = re.sub(r"https?://[^\s]+", " ", text)
        text = re.sub(
            r"(复制此链接.*$|打开Dou音搜索.*$|直接观看视频.*$)",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []
        return [text]

    def _extract_text_from_item_api(self, video_id: str) -> list[str]:
        api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}"
        request = urllib.request.Request(
            api_url,
            headers={"User-Agent": self.USER_AGENT},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                raw = response.read().decode("utf-8", errors="ignore")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            return []

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []

        item_list = payload.get("item_list")
        if not isinstance(item_list, list) or not item_list:
            return []

        item = item_list[0] if isinstance(item_list[0], dict) else {}
        results: list[str] = []
        desc = self._clean_text(str(item.get("desc", "")))
        if desc:
            results.append(desc)

        author = item.get("author")
        if isinstance(author, dict):
            nickname = self._clean_text(str(author.get("nickname", "")))
            signature = self._clean_text(str(author.get("signature", "")))
            if nickname:
                results.append(f"作者: {nickname}")
            if signature:
                results.append(f"作者简介: {signature}")

        text_extra = item.get("text_extra")
        if isinstance(text_extra, list):
            hashtags = []
            for tag in text_extra:
                if not isinstance(tag, dict):
                    continue
                hashtag_name = self._clean_text(str(tag.get("hashtag_name", "")))
                if hashtag_name:
                    hashtags.append(f"#{hashtag_name}")
            if hashtags:
                results.append("话题: " + " ".join(hashtags[:12]))

        return results

    def _extract_meta_text(self, html_text: str) -> list[str]:
        results: list[str] = []
        patterns = [
            r'<meta\s+property="og:title"\s+content="([^"]+)"',
            r'<meta\s+name="description"\s+content="([^"]+)"',
            r'<meta\s+property="og:description"\s+content="([^"]+)"',
            r"<title>(.*?)</title>",
        ]
        for pattern in patterns:
            for match in re.findall(pattern, html_text, flags=re.IGNORECASE | re.DOTALL):
                text = self._clean_text(match)
                if text:
                    results.append(text)
        return results

    def _extract_json_text(self, html_text: str) -> list[str]:
        results: list[str] = []
        # 常见字段名，覆盖标题、描述、标签、字幕类信息
        key_pattern = r'"(?:desc|title|text|caption|subtitle|ocr|content|hashtag_name)"\s*:\s*"([^"]+)"'
        for match in re.findall(key_pattern, html_text, flags=re.IGNORECASE):
            text = self._clean_text(match)
            if text and len(text) > 1:
                results.append(text)

        # 兼容部分页面的 JSON blob（尽量解析字符串值）
        script_matches = re.findall(
            r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for raw_json in script_matches:
            raw_json = raw_json.strip()
            if not raw_json:
                continue
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                continue
            results.extend(self._collect_text_from_json(data))
        return results

    def _collect_text_from_json(self, data) -> list[str]:
        results: list[str] = []
        if isinstance(data, dict):
            for _, value in data.items():
                results.extend(self._collect_text_from_json(value))
        elif isinstance(data, list):
            for item in data:
                results.extend(self._collect_text_from_json(item))
        elif isinstance(data, str):
            text = self._clean_text(data)
            if 3 <= len(text) <= 300:
                if any(tag in text.lower() for tag in ["douyin", "http://", "https://"]):
                    return results
                results.append(text)
        return results

    def _merge_chunks(self, chunks: list[str]) -> str:
        deduped: list[str] = []
        seen = set()
        for chunk in chunks:
            normalized = chunk.strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(normalized)
            if len(deduped) >= 60:
                break
        return "\n".join(deduped)

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = html.unescape(text)
        cleaned = re.sub(r"\\u[0-9a-fA-F]{4}", " ", cleaned)
        cleaned = cleaned.replace("\\n", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
