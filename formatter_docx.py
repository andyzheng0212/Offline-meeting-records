"""Generate meeting minutes document using python-docx."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from docx import Document  # type: ignore
from docx.shared import Pt


def _add_heading(document: Document, text: str, level: int = 1) -> None:
    paragraph = document.add_heading(level=level)
    run = paragraph.add_run(text)
    run.bold = True


def _add_kv_paragraph(document: Document, key: str, value: str) -> None:
    paragraph = document.add_paragraph()
    run_key = paragraph.add_run(f"{key}：")
    run_key.bold = True
    paragraph.add_run(value)


def load_action_items(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def create_minutes_document(
    output_path: Path,
    meeting_info: Dict[str, str],
    summary_title: str,
    summary_content: str,
    diff_content: Optional[str],
    action_items: List[Dict[str, str]],
    policy_suggestions: List[Dict[str, str]],
) -> Path:
    document = Document()
    document.styles["Normal"].font.size = Pt(11)

    document.add_heading(meeting_info.get("title", "会议纪要"), level=0)

    base_fields = [
        ("会议主题", meeting_info.get("topic", "")),
        ("时间地点", meeting_info.get("time_place", "")),
        ("主持人", meeting_info.get("host", "")),
        ("记录人", meeting_info.get("recorder", "")),
        ("与会人员", meeting_info.get("participants", "")),
    ]
    for key, value in base_fields:
        _add_kv_paragraph(document, key, value)

    _add_heading(document, "议题要点", level=1)
    document.add_paragraph(summary_title, style=None)
    for line in summary_content.splitlines():
        if line.startswith("-"):
            document.add_paragraph(line[1:].strip(), style="List Bullet")
        elif line.strip():
            document.add_paragraph(line.strip())

    if diff_content:
        _add_heading(document, "录音校对差异", level=1)
        for line in diff_content.splitlines():
            if line.startswith("##"):
                paragraph = document.add_paragraph()
                run = paragraph.add_run(line.replace("##", "").strip())
                run.bold = True
            elif line.startswith("-"):
                document.add_paragraph(line[1:].strip(), style="List Bullet")
            elif line.strip():
                document.add_paragraph(line.strip())

    _add_heading(document, "行动项清单", level=1)
    if action_items:
        table = document.add_table(rows=1, cols=3)
        header_cells = table.rows[0].cells
        headers = ["责任人", "事项", "时间节点"]
        for cell, text in zip(header_cells, headers):
            paragraph = cell.paragraphs[0]
            run = paragraph.add_run(text)
            run.bold = True
        for item in action_items:
            row_cells = table.add_row().cells
            row_cells[0].text = item.get("who", "")
            row_cells[1].text = item.get("what", "")
            row_cells[2].text = item.get("when", "")
    else:
        document.add_paragraph("暂无行动项。")

    _add_heading(document, "制度提示表", level=1)
    document.add_paragraph("以下提示仅供参考，不构成合规结论。")
    if policy_suggestions:
        table = document.add_table(rows=1, cols=4)
        header_cells = table.rows[0].cells
        headers = ["制度标题", "条款", "来源", "摘要"]
        for cell, text in zip(header_cells, headers):
            paragraph = cell.paragraphs[0]
            run = paragraph.add_run(text)
            run.bold = True
        for suggestion in policy_suggestions:
            row = table.add_row().cells
            row[0].text = suggestion.get("title", "")
            row[1].text = suggestion.get("section", "")
            row[2].text = suggestion.get("source", "")
            row[3].text = suggestion.get("snippet", "")
    else:
        document.add_paragraph("未匹配到相关制度。")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path
