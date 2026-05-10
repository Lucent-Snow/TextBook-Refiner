from backend.loaders.base import Page
from backend.loaders.pdf import (
    _detect_chapters_by_heuristics,
    _detect_mineru_headings,
    _is_text_quality_acceptable,
)


def test_pdf_heuristic_chapter_regex_handles_no_toc_fallback():
    chapters = _detect_chapters_by_heuristics([
        Page(number=1, text="第一章 绪论\n正文内容"),
    ])

    assert len(chapters) == 1
    assert chapters[0].title == "第一章 绪论"


def test_pdf_text_quality_rejects_mojibake():
    bad_text = "����" * 100
    good_text = "第一章 绪论\n" + "炎症是机体对损伤因子的防御性反应。" * 30

    assert not _is_text_quality_acceptable(bad_text)
    assert _is_text_quality_acceptable(good_text)


def test_mineru_headings_normalize_levels_and_skip_toc_page_numbers():
    markdown = "\n".join([
        "# 第一章 细胞和组织的适应与损伤 5",
        "# 第一节　适应. 5",
        "# 第一章 细胞和组织的适应与损伤",
        "# 第一节 | 适 应",
        "# 一、萎缩",
        "# 版权所有，侵权必究！",
    ])

    chapters = _detect_mineru_headings(markdown)

    assert [chapter.title for chapter in chapters] == [
        "第一章 细胞和组织的适应与损伤",
        "第一节 适 应",
        "一、萎缩",
    ]
    assert [chapter.level for chapter in chapters] == [1, 2, 3]
