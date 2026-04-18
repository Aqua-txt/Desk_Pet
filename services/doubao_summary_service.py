from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from pathlib import Path


def load_dotenv_file() -> None:
    """轻量读取项目根目录 .env（不依赖第三方库）。"""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and (key not in os.environ or not os.environ.get(key, "").strip()):
            os.environ[key] = value


load_dotenv_file()


class DoubaoSummaryService:
    """
    调用 Doubao-Seed-2.0-lite 生成视频总结。

    环境变量：
    - DOUBAO_API_KEY: 必填
    - DOUBAO_MODEL: 可选，默认 doubao-seed-2.0-lite
    - DOUBAO_BASE_URL: 可选，默认火山引擎 Ark OpenAI 兼容地址
    """

    def __init__(self):
        self.api_key = os.getenv("DOUBAO_API_KEY", "").strip()
        self.model = os.getenv("DOUBAO_MODEL", "doubao-seed-2.0-lite").strip()
        self.base_url = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").strip()

    def summarize_video_content(self, resolved_url: str, extracted_text: str) -> str:
        if not self.api_key:
            raise RuntimeError("未检测到 DOUBAO_API_KEY，请先在环境变量中配置。")

        prompt = (
            "你是视频内容分析助手。请根据给定的抖音视频文本信息，输出结构化总结。\n"
            "要求：\n"
            "1) 先给 3-5 条关键要点；\n"
            "2) 再给 1 段简短摘要；\n"
            "3) 输出 5 个关键词；\n"
            "4) 如果信息不足，请明确写出不确定项，不要编造。\n\n"
            f"视频链接: {resolved_url}\n"
            "提取到的文本信息如下：\n"
            f"{extracted_text}"
        )

        endpoint = f"{self.base_url}/chat/completions"
        model_candidates = self._build_model_candidates(self.model)
        last_error = ""

        for candidate in model_candidates:
            request_body = {
                "model": candidate,
                "messages": [
                    {"role": "system", "content": "你是严谨且简洁的中文视频总结助手。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            }
            request = urllib.request.Request(
                endpoint,
                data=json.dumps(request_body).encode("utf-8"),
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )

            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    raw_response = response.read().decode("utf-8", errors="ignore")
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="ignore")
                # 404 且模型/端点不存在时，继续尝试下一种模型写法
                if exc.code == 404 and "InvalidEndpointOrModel.NotFound" in body:
                    last_error = body
                    continue
                raise RuntimeError(f"Doubao API 请求失败: HTTP {exc.code}, {body}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(f"Doubao API 网络错误: {exc.reason}") from exc
            except (TimeoutError, socket.timeout) as exc:
                raise RuntimeError("Doubao API 请求超时，请稍后重试。") from exc

            try:
                payload = json.loads(raw_response)
                return payload["choices"][0]["message"]["content"].strip()
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(f"Doubao API 返回格式异常: {raw_response}") from exc

        raise RuntimeError(
            "Doubao API 请求失败: 模型或端点不存在。"
            f"当前 DOUBAO_MODEL={self.model}。"
            "请改为火山 Ark 控制台可用的 Endpoint ID（通常是 ep-...）。"
            f"服务返回: {last_error}"
        )

    @staticmethod
    def _build_model_candidates(model: str) -> list[str]:
        variants = [model.strip()]
        lower_variant = variants[0].lower()
        if lower_variant not in variants:
            variants.append(lower_variant)

        dot_to_dash = lower_variant.replace("2.0", "2-0")
        if dot_to_dash not in variants:
            variants.append(dot_to_dash)

        return [item for item in variants if item]
