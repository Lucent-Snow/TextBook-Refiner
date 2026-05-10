from backend.loaders.base import Page
from backend.loaders.pdf import _detect_chapters_by_heuristics


def test_pdf_heuristic_chapter_regex_handles_no_toc_fallback():
    chapters = _detect_chapters_by_heuristics([
        Page(number=1, text="第一章 绪论\n正文内容"),
    ])

    assert len(chapters) == 1
    assert chapters[0].title == "第一章 绪论"
