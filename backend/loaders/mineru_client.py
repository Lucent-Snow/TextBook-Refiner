"""MinerU PDF parsing adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.core.config import settings

logger = logging.getLogger(__name__)


class MinerUParseError(RuntimeError):
    """Raised when MinerU parsing cannot produce Markdown."""


@dataclass
class MinerUParseResult:
    markdown_path: Path
    output_dir: Path
    page_count: int


def parse_pdf_with_mineru(filepath: str | Path) -> MinerUParseResult:
    """Parse a PDF with MinerU, splitting it into API-sized page ranges."""
    source = Path(filepath)
    if not source.exists():
        raise MinerUParseError(f"PDF file does not exist: {source}")

    script_dir = _script_dir()
    python_exe = _python_executable(script_dir)
    process_script = script_dir / "process_document.py"
    if not process_script.exists():
        raise MinerUParseError(f"MinerU process script not found: {process_script}")

    output_dir = _output_dir(source)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_count = _get_pdf_page_count(source)
    segments = _split_pdf(source, output_dir, page_count)
    logger.info(
        "MinerU PDF parsing started",
        extra={
            "file_type": "pdf",
            "byte_size": source.stat().st_size,
            "page_count": page_count,
            "segments": len(segments),
        },
    )

    env_overrides = _mineru_env_overrides()
    try:
        segment_markdowns: list[Path] = []
        for segment in segments:
            _run_mineru_document(
                python_exe=python_exe,
                process_script=process_script,
                source=segment,
                output_dir=output_dir,
                env_overrides=env_overrides,
            )
            md_path = output_dir / f"{segment.stem}.md"
            if not md_path.exists():
                raise MinerUParseError(f"MinerU did not produce Markdown for {segment.name}")
            segment_markdowns.append(md_path)
    finally:
        _cleanup_env_overrides(env_overrides)

    merged = output_dir / f"{source.stem}.mineru.md"
    _merge_markdown_segments(segment_markdowns, merged)
    logger.info(
        "MinerU PDF parsing completed",
        extra={
            "file_type": "pdf",
            "page_count": page_count,
            "segments": len(segments),
            "markdown_bytes": merged.stat().st_size,
        },
    )
    return MinerUParseResult(markdown_path=merged, output_dir=output_dir, page_count=page_count)


def _script_dir() -> Path:
    if settings.mineru_script_dir:
        return Path(settings.mineru_script_dir)
    return Path.home() / ".claude" / "skills-backup" / "mineru-skill" / "scripts"


def _python_executable(script_dir: Path) -> Path:
    if settings.mineru_python:
        return Path(settings.mineru_python)
    if os.name == "nt":
        return script_dir / ".venv" / "Scripts" / "python.exe"
    return script_dir / ".venv" / "bin" / "python3"


def _output_dir(source: Path) -> Path:
    base = Path(settings.mineru_output_dir) if settings.mineru_output_dir else Path(settings.data_root) / "mineru"
    safe_stem = re.sub(r"[^A-Za-z0-9_.\-\u4e00-\u9fff]+", "_", source.stem)
    return base / safe_stem


def _mineru_env_overrides() -> dict[str, str]:
    if not settings.mineru_api_key:
        return {}

    data_dir = Path(tempfile.mkdtemp(prefix="mineru-token-"))
    token_file = data_dir / "all_tokens.json"
    token_payload = {
        "env": {
            "name": "env",
            "token_name": "env",
            "token": settings.mineru_api_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expired_at": "2099-01-01T00:00:00Z",
        }
    }
    token_file.write_text(json.dumps(token_payload), encoding="utf-8")
    return {"MINERU_DATA_DIR": str(data_dir)}


def _cleanup_env_overrides(env_overrides: dict[str, str]) -> None:
    data_dir = env_overrides.get("MINERU_DATA_DIR")
    if data_dir:
        shutil.rmtree(data_dir, ignore_errors=True)


def _get_pdf_page_count(source: Path) -> int:
    try:
        import fitz
    except ImportError as exc:
        raise MinerUParseError("PyMuPDF is required to split PDFs for MinerU") from exc

    doc = fitz.open(str(source))
    try:
        return doc.page_count
    finally:
        doc.close()


def _split_pdf(source: Path, output_dir: Path, page_count: int) -> list[Path]:
    max_pages = max(1, min(settings.mineru_max_pages, 200))
    ranges = [(start, min(start + max_pages - 1, page_count - 1)) for start in range(0, page_count, max_pages)]
    return _write_ranges(source, output_dir, ranges)


def _write_ranges(source: Path, output_dir: Path, ranges: list[tuple[int, int]]) -> list[Path]:
    try:
        import fitz
    except ImportError as exc:
        raise MinerUParseError("PyMuPDF is required to split PDFs for MinerU") from exc

    max_bytes = max(1, settings.mineru_max_file_mb) * 1024 * 1024
    written: list[Path] = []
    queue = list(ranges)

    while queue:
        start, end = queue.pop(0)
        segment = output_dir / f"{source.stem}_p{start + 1:04d}-{end + 1:04d}.pdf"
        src_doc = fitz.open(str(source))
        out_doc = fitz.open()
        try:
            out_doc.insert_pdf(src_doc, from_page=start, to_page=end)
            out_doc.save(segment)
        finally:
            out_doc.close()
            src_doc.close()

        if segment.stat().st_size > max_bytes and start < end:
            segment.unlink(missing_ok=True)
            mid = (start + end) // 2
            queue.insert(0, (mid + 1, end))
            queue.insert(0, (start, mid))
            continue

        written.append(segment)

    return written


def _run_mineru_document(
    *,
    python_exe: Path,
    process_script: Path,
    source: Path,
    output_dir: Path,
    env_overrides: dict[str, str],
) -> None:
    cmd = [
        str(python_exe),
        str(process_script),
        str(source),
        "--output-dir",
        str(output_dir),
        "--model",
        settings.mineru_model,
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(env_overrides)

    completed = subprocess.run(
        cmd,
        cwd=str(process_script.parent),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=settings.mineru_timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        logger.error(
            "MinerU segment parsing failed",
            extra={"file_type": "pdf", "segment": source.name, "return_code": completed.returncode},
        )
        message = _last_nonempty_line(completed.stdout) or _last_nonempty_line(completed.stderr)
        raise MinerUParseError(message or f"MinerU failed for {source.name}")


def _last_nonempty_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        clean = line.strip()
        if clean:
            return clean
    return ""


def _merge_markdown_segments(segment_markdowns: list[Path], output_path: Path) -> None:
    parts: list[str] = []
    for md_path in segment_markdowns:
        text = md_path.read_text(encoding="utf-8")
        image_dir = f"{md_path.stem}_images"
        text = text.replace("](images/", f"]({image_dir}/")
        parts.append(text.strip())
    output_path.write_text("\n\n".join(parts).strip() + "\n", encoding="utf-8")
