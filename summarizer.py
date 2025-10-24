"""Summarization and action item extraction utilities."""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from typing import Iterable, List, Optional
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from textrank4zh import TextRank4Sentence  # type: ignore

ACTION_PATTERN = re.compile(
    r"(?P<who>[\u4e00-\u9fa5A-Za-z0-9·\-]{1,8})[^\u4e00-\u9fa5A-Za-z0-9]{0,3}(负责|完成|落实|推进|跟进|执行)"
    r"(?P<who>[\u4e00-\u9fa5A-Za-z0-9]+)[^\u4e00-\u9fa5A-Za-z0-9]{0,3}(负责|完成|落实|推进|跟进)"
    r"(?P<what>[^。；，,.]*?)"
    r"(于|在)(?P<when>[^。；，,.]*(\d{4}-\d{2}-\d{2}|本周|下周|月底|尽快))",
)


@dataclass
class ActionItem:
    who: str
    what: str
    when: str

    def to_dict(self) -> dict:
        return {"who": self.who, "what": self.what, "when": self.when}


class PersonDictionary:
    """Load and resolve person names from a contact CSV file."""

    def __init__(self, csv_path: Optional[Path]) -> None:
        self.names: List[str] = []
        if csv_path and csv_path.exists():
            self.names = self._load_names(csv_path)

    @staticmethod
    def _load_names(csv_path: Path) -> List[str]:
        names: List[str] = []
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                name_key = "name" if "name" in reader.fieldnames else reader.fieldnames[0]
                for row in reader:
                    value = (row.get(name_key) or "").strip()
                    if value:
                        names.append(value)
            else:
                f.seek(0)
                for line in f:
                    value = line.strip()
                    if value:
                        names.append(value)
        # 去重并按长度排序，长名称优先匹配
        unique = sorted(set(names), key=lambda item: (-len(item), item))
        return unique

    def resolve(self, candidate_text: str) -> Optional[str]:
        if not self.names:
            return None
        for name in self.names:
            if name in candidate_text:
                return name
        matches = get_close_matches(candidate_text.strip(), self.names, n=1, cutoff=0.7)
        return matches[0] if matches else None

    @property
    def loaded(self) -> bool:
        return bool(self.names)


class SummaryBuilder:
    """Create quick and proofreading summaries."""

    def __init__(self, summary_dir: Path, person_dict: PersonDictionary) -> None:
        self.summary_dir = summary_dir
        self.summary_dir.mkdir(parents=True, exist_ok=True)
        self.person_dict = person_dict
class SummaryBuilder:
    """Create quick and proofreading summaries."""

    def __init__(self, summary_dir: Path) -> None:
        self.summary_dir = summary_dir
        self.summary_dir.mkdir(parents=True, exist_ok=True)

    def generate_quick_summary(self, notes: Iterable[str], filename: str) -> Path:
        """Create a markdown quick summary from user provided notes."""

        notes_list = [note.strip() for note in notes if note.strip()]
        content_lines = ["# 快速版纪要", ""]
        for idx, note in enumerate(notes_list, start=1):
            content_lines.append(f"- {idx}. {note}")
        content = "\n".join(content_lines) + "\n"
        output_path = self.summary_dir / filename
        output_path.write_text(content, encoding="utf-8")
        self._save_action_items(notes_list)
        return output_path

    def _save_action_items(self, notes: List[str]) -> Path:
        items = [
            item.to_dict()
            for item in extract_action_items("\n".join(notes), person_dict=self.person_dict)
        ]
        items = [item.to_dict() for item in extract_action_items("\n".join(notes))]
        action_path = self.summary_dir / "actions.json"
        action_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        return action_path

    def generate_proofreading_summary(self, transcript: str, prefix: str) -> Path:
        """Use TextRank to summarize transcript for proofreading."""

        if not transcript.strip():
            raise ValueError("转写内容为空，无法生成校对摘要。")
        textrank = TextRank4Sentence()
        textrank.analyze(text=transcript, lower=True, source="all_filters")
        sentences = [sent.sentence for sent in textrank.get_key_sentences(num=10)]
        content_lines = ["# 录音校对摘要", ""]
        for sentence in sentences:
            content_lines.append(f"- {sentence.strip()}")
        output_name = f"{prefix}{self._timestamp()}.md"
        output_path = self.summary_dir / output_name
        output_path.write_text("\n".join(content_lines) + "\n", encoding="utf-8")
        return output_path

    def generate_diff_report(self, quick_text: str, proof_text: str, prefix: str) -> Path:
        """Produce a simple diff between quick summary and proof summary."""

        quick_set = set(line.strip("- ") for line in quick_text.splitlines() if line.startswith("-"))
        proof_set = set(line.strip("- ") for line in proof_text.splitlines() if line.startswith("-"))
        missing_in_quick = sorted(proof_set - quick_set)
        missing_in_proof = sorted(quick_set - proof_set)
        lines = ["# 录音与快速版差异报告", ""]
        lines.append("## 录音出现但快版缺失")
        if missing_in_quick:
            for item in missing_in_quick:
                lines.append(f"- {item}")
        else:
            lines.append("- 无")
        lines.append("")
        lines.append("## 快版提及但录音未捕获")
        if missing_in_proof:
            for item in missing_in_proof:
                lines.append(f"- {item}")
        else:
            lines.append("- 无")
        output_path = self.summary_dir / f"{prefix}{self._timestamp()}.md"
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return output_path

    @staticmethod
    def _timestamp() -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")


def extract_action_items(text: str, person_dict: Optional[PersonDictionary] = None) -> List[ActionItem]:
    matches: List[ActionItem] = []
    for match in ACTION_PATTERN.finditer(text):
        candidate = match.group("who")
        resolved = None
        if person_dict:
            resolved = person_dict.resolve(match.group(0))
        who = resolved or candidate
def extract_action_items(text: str) -> List[ActionItem]:
    matches: List[ActionItem] = []
    for match in ACTION_PATTERN.finditer(text):
        who = match.group("who")
        what = match.group("what").strip()
        when = match.group("when")
        matches.append(ActionItem(who=who, what=what, when=when))
    return matches


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_summarizer(config: dict, base_path: Path) -> SummaryBuilder:
    summary_dir = base_path / config["paths"]["summary_dir"]
    contact_csv = config["summary"].get("contact_csv")
    contact_path = base_path / contact_csv if contact_csv else None
    person_dict = PersonDictionary(contact_path)
    return SummaryBuilder(summary_dir, person_dict)
    return SummaryBuilder(summary_dir)
