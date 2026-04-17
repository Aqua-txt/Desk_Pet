from __future__ import annotations

from dataclasses import dataclass

from services.doubao_summary_service import DoubaoSummaryService
from services.douyin_content_extractor import DouyinContentExtractor
from services.douyin_resolver import DouyinResolver


@dataclass
class PipelineResult:
    raw_input: str
    short_url: str
    resolved_url: str
    extracted_text: str
    summary: str


class DouyinSummaryPipeline:
    """链接解析 -> 内容提取(ASR/OCR文本近似) -> Doubao总结。"""

    def __init__(self):
        self.resolver = DouyinResolver()
        self.extractor = DouyinContentExtractor()
        self.summarizer = DoubaoSummaryService()

    def run(self, raw_input: str) -> PipelineResult:
        short_url = self.resolver.extract_short_url(raw_input)
        resolved_url = self.resolver.resolve(short_url)

        try:
            video_id = self.resolver.extract_video_id(resolved_url)
            extracted_text = self.extractor.extract(
                resolved_url=resolved_url,
                raw_input_text=raw_input,
                video_id=video_id,
            )
        except Exception:
            # 内容提取异常时使用用户原始输入兜底，保证仍可总结
            extracted_text = raw_input.strip()

        summary = self.summarizer.summarize_video_content(
            resolved_url=resolved_url,
            extracted_text=extracted_text,
        )
        return PipelineResult(
            raw_input=raw_input.strip(),
            short_url=short_url,
            resolved_url=resolved_url,
            extracted_text=extracted_text,
            summary=summary,
        )
