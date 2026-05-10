from backend.loaders.markdown import load_markdown
from backend.models.material import FileType, Material
from backend.processing.sectioning import recognize_sections


def test_markdown_chapters_keep_body_text(tmp_path):
    path = tmp_path / "book.md"
    path.write_text("# 第一章 绪论\n炎症是防御反应。\n# 第二章 机制\n白细胞参与炎症。", encoding="utf-8")
    document = load_markdown(path)
    material = Material(
        id="mat_md",
        project_id="proj_md",
        filename="book.md",
        file_type=FileType.MARKDOWN,
        file_path=str(path),
    )

    sections = recognize_sections(material, document)

    assert len(sections) == 2
    assert "炎症是防御反应" in sections[0].text
    assert "白细胞参与炎症" in sections[1].text
