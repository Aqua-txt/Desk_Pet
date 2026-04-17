from __future__ import annotations

import re
import urllib.error
import urllib.request
from urllib.parse import urlparse


class DouyinResolver:
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )

    def extract_short_url(self, raw_text: str) -> str:
        text = raw_text.strip()
        if not text:
            raise ValueError("输入不能为空。")

        match = re.search(r"https?://[^\s]+", text)
        candidate = match.group(0) if match else text
        candidate = candidate.rstrip("`'\"，。,.!！；;）)")

        if "douyin.com" not in candidate:
            raise ValueError("请输入有效的抖音链接。")
        return candidate

    def resolve(self, short_url: str) -> str:
        request = urllib.request.Request(
            short_url,
            headers={"User-Agent": self.USER_AGENT},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                final_url = response.geturl()
        except Exception:
            # 解析失败时回退到短链，避免整条总结流程中断
            return short_url

        if "douyin.com" not in final_url:
            return short_url
        return final_url

    def extract_video_id(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path or ""
        match = re.search(r"/video/(\d+)", path)
        if match:
            return match.group(1)
        return ""
