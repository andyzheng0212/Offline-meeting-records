"""Offline Meeting Records main GUI application."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import PySimpleGUI as sg
import yaml

from asr_vosk import ASRBackend, build_asr
from asr_vosk import ASRModel, build_asr
from destroyer import Destroyer, build_destroyer
from formatter_docx import create_minutes_document, load_action_items
from policy_db import PolicyDatabase, build_policy_db
from recorder import AudioRecorder, RecorderError, build_recorder
from summarizer import SummaryBuilder, build_summarizer, load_text


@dataclass
class AppState:
    quick_summary_path: Optional[Path] = None
    proofreading_path: Optional[Path] = None
    diff_path: Optional[Path] = None
    transcript_path: Optional[Path] = None
    policy_results: List[dict] = field(default_factory=list)


class OfflineMeetingApp:
    def __init__(self, config_path: Path) -> None:
        self.base_path = config_path.parent
        self.config = self._load_config(config_path)
        self.pending_warnings: List[str] = []
        self.model_path = self.base_path / self.config["asr"]["model_path"]
        self.recorder: AudioRecorder = build_recorder(self.config, self.base_path)
        self.summarizer: SummaryBuilder = build_summarizer(self.config, self.base_path)
        self.person_dict = self.summarizer.person_dict
        self.destroyer: Destroyer = build_destroyer(self.config, self.base_path)
        self.policy_db: PolicyDatabase = build_policy_db(self.config, self.base_path)
        self.window: Optional[sg.Window] = None
        self.asr: Optional[ASRBackend] = None
        if not self.model_path.exists():
            self.pending_warnings.append(
                "未检测到 Vosk 中文模型，请下载并解压到 models/vosk-model-cn 目录。具体步骤见 README。"
            )
        else:
            try:
                self.asr = build_asr(self.config, self.base_path)
            except Exception as exc:  # Model issues
                self.pending_warnings.append(f"Vosk 模型加载失败：{exc}")
                self.asr = None
        try:
            self.asr: Optional[ASRModel] = build_asr(self.config, self.base_path)
        except Exception as exc:  # Model missing etc.
            sg.popup_error(f"Vosk 模型加载失败：{exc}")
            self.asr = None
        self.state = AppState()
        self.paths = self.config["paths"]
        self.summary_cfg = self.config["summary"]
        self.storage_cfg = self.config["storage"]

    def _load_config(self, path: Path) -> dict:
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def run(self) -> None:
        sg.theme("DarkBlue3")

        info_frame = sg.Frame(
            "会议信息",
            [
                [
                    sg.Text("会议标题", size=(8, 1)),
                    sg.Input(key="title", expand_x=True),
                    sg.Text("会议主题", size=(8, 1)),
                    sg.Input(key="topic", expand_x=True),
                ],
                [
                    sg.Text("时间地点", size=(8, 1)),
                    sg.Input(key="time_place", expand_x=True),
                    sg.Text("主持人", size=(8, 1)),
                    sg.Input(key="host", expand_x=True),
                ],
                [
                    sg.Text("记录人", size=(8, 1)),
                    sg.Input(key="recorder", expand_x=True),
                    sg.Text("与会人员", size=(8, 1)),
                    sg.Input(key="participants", expand_x=True),
                ],
            ],
            expand_x=True,
        )

        tab_notes = [
            [
                sg.Text("要点条目（每行一条）", font=("Microsoft YaHei", 11, "bold")),
                sg.Text(
                    f"责任人词典：{'已加载' if self.person_dict.loaded else '未加载'}",
                    key="contact_status",
                    text_color="#F7F7F7",
                ),
            ],
            [
                sg.Multiline(
                    key="notes",
                    size=(80, 12),
                    expand_x=True,
                    expand_y=True,
                    tooltip="请输入会议要点，每行一条，生成快速版纪要。",
                )
            ],
            [
                sg.Button("生成快速版", size=(14, 1), button_color=("white", "#1E88E5")),
                sg.Button("查看行动项", key="查看行动项", size=(14, 1)),
            ],
        ]

        asr_text, asr_color = self._current_asr_status()
        tab_record = [
            [
                sg.Button("开始录音", size=(12, 1), button_color=("white", "#43A047")),
                sg.Button("标记重点", size=(12, 1)),
                sg.Button("停止录音", size=(12, 1), button_color=("white", "#E53935")),
            ],
            [
                sg.Button("录音校对", size=(12, 1), button_color=("white", "#8E24AA")),
                sg.Text("ASR 状态："),
                sg.Text(
                    asr_text,
                    key="asr_status",
                    text_color=asr_color,
                    "已就绪" if self.asr else "未加载",
                    key="asr_status",
                    text_color="#FFEB3B" if not self.asr else "#C5E1A5",
                ),
            ],
        ]

        template_options = ["通用", "党委会", "项目会", "招采会"]
        default_template = self.config["summary"].get("default_template", "通用")
        if default_template not in template_options:
            default_template = "通用"
        tab_policy = [
            [
                sg.Button("导入政策库", size=(14, 1)),
                sg.Button("政策对照", size=(14, 1)),
                sg.Button("一键销毁", size=(14, 1)),
            ],
            [
                sg.Text("纪要模板"),
                sg.Combo(
                    template_options,
                    default_value=default_template,
                    key="template_choice",
                    readonly=True,
                    size=(15, 1),
                ),
                sg.Button("导出纪要", size=(14, 1), button_color=("white", "#3949AB")),
            ],
        ]

        tab_group = sg.TabGroup(
            [
                [
                    sg.Tab("纪要撰写", tab_notes, key="tab_notes"),
                    sg.Tab("录音与校对", tab_record, key="tab_record"),
                    sg.Tab("制度与导出", tab_policy, key="tab_policy"),
                ]
            ],
            expand_x=True,
            expand_y=True,
        )

        log_frame = sg.Frame(
            "系统消息",
            [[sg.Multiline(key="log", size=(100, 10), disabled=True, autoscroll=True, expand_x=True, expand_y=True)]],
            expand_x=True,
            expand_y=True,
        )

        layout = [
            [sg.Text("Offline Meeting Records", font=("Microsoft YaHei", 16, "bold"))],
            [info_frame],
            [tab_group],
            [log_frame],
            [sg.StatusBar("就绪", key="status_bar", size=(60, 1))],
        ]

        window = sg.Window(
            "Offline Meeting Records",
            layout,
            finalize=True,
            resizable=True,
            element_justification="left",
        )
        self.window = window
        self._refresh_contact_status()
        self._update_asr_status()
        self._show_startup_warnings()
        sg.theme("SystemDefault")
        layout = [
            [sg.Text("会议标题"), sg.Input(key="title", size=(25, 1)), sg.Text("会议主题"), sg.Input(key="topic", size=(25, 1))],
            [sg.Text("时间地点"), sg.Input(key="time_place", size=(25, 1)), sg.Text("主持人"), sg.Input(key="host", size=(25, 1))],
            [sg.Text("记录人"), sg.Input(key="recorder", size=(25, 1)), sg.Text("与会人员"), sg.Input(key="participants", size=(25, 1))],
            [sg.Text("要点条目 (每行一条)"), sg.Multiline(key="notes", size=(80, 8))],
            [
                sg.Button("开始录音"),
                sg.Button("标记重点"),
                sg.Button("停止录音"),
                sg.Button("生成快速版"),
                sg.Button("录音校对"),
                sg.Button("导入政策库"),
                sg.Button("政策对照"),
                sg.Button("导出纪要"),
                sg.Button("一键销毁"),
            ],
            [sg.Multiline(key="log", size=(100, 12), disabled=True, autoscroll=True)],
        ]
        window = sg.Window("Offline Meeting Records", layout, finalize=True, resizable=True)
        self.window = window
        while True:
            event, values = window.read(timeout=500)
            if event == sg.WIN_CLOSED:
                break
            if event == sg.TIMEOUT_EVENT:
                continue
            try:
                if event == "开始录音":
                    self.handle_start_recording()
                elif event == "标记重点":
                    self.handle_mark()
                elif event == "停止录音":
                    self.handle_stop_recording()
                elif event == "生成快速版":
                    self.handle_quick_summary(values.get("notes", ""))
                elif event == "查看行动项":
                    self.handle_view_actions()
                elif event == "录音校对":
                    self.handle_proofreading()
                elif event == "导入政策库":
                    self.handle_import_policies()
                elif event == "政策对照":
                    self.handle_policy_lookup()
                elif event == "导出纪要":
                    self.handle_export(values)
                elif event == "一键销毁":
                    self.handle_destroy()
            except Exception as exc:
                self.log(f"操作失败：{exc}")
                sg.popup_error(str(exc))
        window.close()
        self.policy_db.close()

    def handle_start_recording(self) -> None:
        try:
            session_id = self.recorder.start()
            self.log(f"录音开始，会话 {session_id}")
            sg.popup("录音已开始。")
            self.set_status("录音进行中…")
            warning = self.recorder.pop_last_warning()
            if warning:
                self.log(warning.replace("\n", " / "))
                sg.popup_ok(warning)
        except RecorderError as exc:
            device_lines = self._list_input_devices()
            message = str(exc)
            if device_lines:
                message = f"{message}\n\n可用输入设备：\n" + "\n".join(device_lines)
            else:
                message = f"{message}\n\n未检测到可用输入设备，请检查麦克风连接。"
            self.log(message.replace("\n", " "))
            sg.popup_error(message)
            sg.popup_error(str(exc))

    def handle_mark(self) -> None:
        label = sg.popup_get_text("请输入标记内容：")
        if not label:
            return
        try:
            self.recorder.mark(label)
            self.log("已标记重点。")
        except RecorderError as exc:
            sg.popup_error(str(exc))

    def handle_stop_recording(self) -> None:
        try:
            markers_path = self.recorder.stop()
            self.log(f"录音已停止，标记保存在 {markers_path.name}")
            sg.popup("录音已停止。")
            self._enforce_retention()
            self.set_status("录音已完成。")
        except RecorderError as exc:
            sg.popup_error(str(exc))

    def handle_quick_summary(self, notes_text: str) -> None:
        notes = notes_text.splitlines()
        output = self.summarizer.generate_quick_summary(notes, self.summary_cfg["quick_filename"])
        self.state.quick_summary_path = output
        self.log(f"快速版纪要已生成：{output.name}")
        sg.popup("快速版纪要已生成。")
        self.set_status("快速版纪要已生成。")

    def handle_proofreading(self) -> None:
        if not self._ensure_asr():
            return
        if not self.asr:
            raise RuntimeError("Vosk 模型未准备，无法进行录音校对。")
        audio_dir = self.base_path / self.paths["audio_dir"]
        wav_files = sorted(audio_dir.glob("*.wav"))
        if not wav_files:
            raise FileNotFoundError("未找到录音文件，请先完成录音。")
        assert self.asr is not None
        transcript_text = self.asr.transcribe_files(wav_files)
        transcript_path = self._write_transcript(transcript_text)
        proof_path = self.summarizer.generate_proofreading_summary(
            transcript_text, self.summary_cfg["proofreading_prefix"]
        )
        self.state.proofreading_path = proof_path
        self.state.transcript_path = transcript_path
        quick_text = ""
        if self.state.quick_summary_path and self.state.quick_summary_path.exists():
            quick_text = load_text(self.state.quick_summary_path)
        proof_text = load_text(proof_path)
        diff_path = self.summarizer.generate_diff_report(
            quick_text, proof_text, self.summary_cfg["diff_prefix"]
        )
        self.state.diff_path = diff_path
        self.log("录音校对完成，已生成摘要与差异报告。")
        sg.popup("录音校对完成。")
        self._enforce_retention()
        self.set_status("录音校对完成。")

    def _write_transcript(self, text: str) -> Path:
        transcript_dir = self.base_path / self.paths["transcript_dir"]
        transcript_dir.mkdir(parents=True, exist_ok=True)
        filename = f"trans_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        transcript_path = transcript_dir / filename
        transcript_path.write_text(text, encoding="utf-8")
        return transcript_path

    def handle_import_policies(self) -> None:
        source_dir = self.base_path / self.paths["policy_source_dir"]
        candidates = [
            f
            for f in source_dir.glob("**/*")
            if f.suffix.lower() in {".pdf", ".docx"} and f.is_file()
        ]
        if not candidates:
            message = "未检测到PDF/Word，将跳过导入。"
            self.log(message)
            sg.popup_ok(message)
            return
        count = self.policy_db.import_sources()
        errors = self.policy_db.pop_last_errors()
        self.log(f"已导入 {count} 条制度内容。")
        message_lines = [f"导入完成，共 {count} 条。仅提示，不构成合规结论。"]
        if errors:
            error_text = "\n".join(errors[:5])
            message_lines.extend(["", "以下文件导入失败（已跳过）：", error_text])
            if len(errors) > 5:
                message_lines.append("……")
            self.log(f"部分制度文件导入失败：{'; '.join(errors)}")
        sg.popup("\n".join(message_lines))
        self.log(f"已导入 {count} 条制度内容。")
        sg.popup(f"导入完成，共 {count} 条。仅提示，不构成合规结论。")

    def handle_policy_lookup(self) -> None:
        query_lines = []
        if self.state.quick_summary_path and self.state.quick_summary_path.exists():
            query_lines.extend(self._extract_query_lines(load_text(self.state.quick_summary_path)))
        if self.state.proofreading_path and self.state.proofreading_path.exists():
            query_lines.extend(self._extract_query_lines(load_text(self.state.proofreading_path)))
        if not query_lines:
            query = sg.popup_get_text("请输入检索关键词：")
            if not query:
                return
            query_lines.append(query)
        unique_queries = list(dict.fromkeys(query_lines))
        results: List[dict] = []
        for query in unique_queries:
            results.extend(self.policy_db.search(query))
        self.state.policy_results = results
        self.log(f"政策对照提示 {len(results)} 条，仅供参考。")
        sg.popup(f"已匹配到 {len(results)} 条制度提示，注意：仅提示，不构成合规结论。")
        self.set_status("政策对照完成。")

    def _extract_query_lines(self, content: str) -> List[str]:
        return [line.lstrip("- ") for line in content.splitlines() if line.startswith("-")]

    def handle_export(self, values: dict) -> None:
        minutes_dir = self.base_path / self.paths["minutes_dir"]
        minutes_dir.mkdir(parents=True, exist_ok=True)
        filename = f"minutes_{time.strftime('%Y%m%d_%H%M%S')}.docx"
        output_path = minutes_dir / filename
        has_proof = self.state.proofreading_path and self.state.proofreading_path.exists()
        summary_title = "录音校对定稿" if has_proof else "快速版纪要"
        summary_title = "快速版纪要" if self.state.quick_summary_path else "录音校对摘要"
        summary_content = ""
        if self.state.proofreading_path and self.state.proofreading_path.exists():
            summary_content = load_text(self.state.proofreading_path)
        elif self.state.quick_summary_path and self.state.quick_summary_path.exists():
            summary_content = load_text(self.state.quick_summary_path)
        diff_content = ""
        if self.state.diff_path and self.state.diff_path.exists():
            diff_content = load_text(self.state.diff_path)
        action_path = self.summarizer.summary_dir / self.summary_cfg["action_items_filename"]
        action_items = load_action_items(action_path)
        meeting_info = {
            "title": values.get("title") or "会议纪要",
            "topic": values.get("topic", ""),
            "time_place": values.get("time_place", ""),
            "host": values.get("host", ""),
            "recorder": values.get("recorder", ""),
            "participants": values.get("participants", ""),
        }
        template_choice = values.get("template_choice") or self.config["summary"].get(
            "default_template", "通用"
        )
        create_minutes_document(
            output_path=output_path,
            meeting_info=meeting_info,
            summary_title=summary_title,
            summary_content=summary_content,
            diff_content=diff_content if diff_content else None,
            action_items=action_items,
            policy_suggestions=self.state.policy_results,
            template_name=template_choice,
        )
        self.log(f"纪要已导出：{output_path.name}")
        sg.popup("纪要已导出。")
        self.set_status(f"纪要已导出（模板：{template_choice}）。")

    def handle_destroy(self) -> None:
        include_minutes = sg.popup_yes_no("是否连同纪要一并销毁？") == "Yes"
        summary = self.destroyer.destroy(include_minutes=include_minutes)
        results = summary["results"]
        lines = []
        for result in results:
            if not result.existed:
                continue
            rel = result.path.relative_to(self.base_path)
            mode_label = "SDelete 覆盖删除" if result.mode == "sdelete" else "普通删除"
            lines.append(f"- {rel}（{mode_label}）")
        if not lines:
            lines.append("- 无需清理（目录为空）")
        message_lines = ["一键销毁完成，已处理以下路径：", *lines]
        if summary.get("fallback_used"):
            fallback_message = summary.get("message") or "已使用普通删除，建议开启全盘加密（如 BitLocker）。"
            message_lines.extend(["", fallback_message])
            self.log(fallback_message)
        self.log("一键销毁完成。")
        sg.popup("\n".join(message_lines))
        )
        self.log(f"纪要已导出：{output_path.name}")
        sg.popup("纪要已导出。")

    def handle_destroy(self) -> None:
        include_minutes = sg.popup_yes_no("是否连同纪要一并销毁？") == "Yes"
        self.destroyer.destroy(include_minutes=include_minutes)
        self.log("一键销毁完成。")
        sg.popup("指定目录已清理。")
        self.set_status("一键销毁完成。")

    def handle_view_actions(self) -> None:
        action_path = self.summarizer.summary_dir / self.summary_cfg["action_items_filename"]
        items = load_action_items(action_path)
        if not items:
            sg.popup("暂无行动项，先录入要点或生成快速版。")
            return
        lines = [f"责任人：{item['who']}\n事项：{item['what']}\n时间：{item['when']}" for item in items]
        sg.popup_scrolled("\n\n".join(lines), title="行动项清单", size=(60, 10))

    def set_status(self, message: str) -> None:
        if self.window and "status_bar" in self.window.AllKeysDict:
            self.window["status_bar"].update(value=message)

    def _refresh_contact_status(self) -> None:
        if self.window and "contact_status" in self.window.AllKeysDict:
            status_text = (
                f"责任人词典：共 {len(self.person_dict.names)} 人"
                if self.person_dict.loaded
                else "责任人词典：未加载"
            )
            self.window["contact_status"].update(status_text)

    def _list_input_devices(self) -> List[str]:
        try:
            import sounddevice as sd  # type: ignore import
        except Exception as exc:
            self.log(f"录音设备自检失败：{exc}")
            return []
        try:
            devices = sd.query_devices()
        except Exception as exc:
            self.log(f"无法查询音频设备：{exc}")
            return []
        lines: List[str] = []
        for index, dev in enumerate(devices):
            max_input = int(dev.get("max_input_channels", 0))
            if max_input <= 0:
                continue
            name = dev.get("name", "未知设备")
            host_idx = dev.get("hostapi")
            host_label = ""
            if host_idx is not None:
                host_label = f" / HostAPI {host_idx}"
            lines.append(f"[{index}] {name}{host_label}（输入通道：{max_input}）")
        return lines

    def _update_asr_status(self) -> None:
        if self.window and "asr_status" in self.window.AllKeysDict:
            text, color = self._current_asr_status()
            self.window["asr_status"].update(text, text_color=color)

    def _current_asr_status(self) -> tuple[str, str]:
        if self.asr:
            return "已就绪", "#C5E1A5"
        return "未加载", "#FFEB3B"

    def _show_startup_warnings(self) -> None:
        for warning in self.pending_warnings:
            self.log(warning)
            sg.popup_ok(warning)
        self.pending_warnings.clear()

    def _ensure_asr(self) -> bool:
        if self.asr:
            return True
        if not self.model_path.exists():
            message = "未检测到 Vosk 中文模型，请下载并解压到 models/vosk-model-cn 目录（详见 README）。"
            self.log(message)
            sg.popup_ok(message)
            return False
        try:
            self.asr = build_asr(self.config, self.base_path)
            self.log("Vosk 模型已加载。")
            self._update_asr_status()
            return True
        except Exception as exc:
            error_message = f"Vosk 模型加载失败：{exc}"
            self.log(error_message)
            sg.popup_error(error_message)
            return False

    def _enforce_retention(self) -> None:
        self._cleanup_by_days(self.base_path / self.paths["audio_dir"], self.storage_cfg.get("retain_audio_days", -1))
        self._cleanup_by_days(
            self.base_path / self.paths["transcript_dir"], self.storage_cfg.get("retain_transcript_days", -1)
        )

    def _cleanup_by_days(self, directory: Path, days: int) -> None:
        if days < 0:
            return
        if not directory.exists():
            return
        cutoff = time.time() - days * 86400
        for item in directory.glob("**/*"):
            try:
                stat = item.stat()
            except FileNotFoundError:
                continue
            if days == 0 or stat.st_mtime < cutoff:
                if item.is_dir():
                    continue
                item.unlink()

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        if hasattr(self, "window") and self.window is not None:
            log_elem = self.window["log"]
            log_elem.update(disabled=False)
            log_elem.print(f"[{timestamp}] {message}")
            log_elem.update(disabled=True)


def main() -> None:
    base_path = Path(__file__).resolve().parent
    config_path = base_path / "config.yaml"
    app = OfflineMeetingApp(config_path)
    app.run()


if __name__ == "__main__":
    main()
