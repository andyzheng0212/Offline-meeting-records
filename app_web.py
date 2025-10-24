"""Streamlit-based offline meeting records web UI."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import streamlit as st
import yaml

from asr_vosk import build_asr
from destroyer import build_destroyer
from formatter_docx import TEMPLATE_PRESETS, create_minutes_document
from policy_db import build_policy_db, PolicyDatabase
from summarizer import SummaryBuilder, build_summarizer

BASE_DIR = Path(__file__).resolve().parent


@st.cache_resource(show_spinner=False)
def load_config() -> Dict:
    with (BASE_DIR / "config.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


CONFIG = load_config()


def ensure_directories(config: Dict) -> None:
    paths = config["paths"]
    for key in [
        "audio_dir",
        "markers_dir",
        "transcript_dir",
        "summary_dir",
        "minutes_dir",
        "policy_source_dir",
        "policy_db_dir",
        "models_dir",
    ]:
        (BASE_DIR / paths[key]).mkdir(parents=True, exist_ok=True)


ensure_directories(CONFIG)


@st.cache_resource(show_spinner=False)
def get_summary_builder() -> SummaryBuilder:
    return build_summarizer(CONFIG, BASE_DIR)


@st.cache_resource(show_spinner=False)
def get_policy_database() -> PolicyDatabase:
    return build_policy_db(CONFIG, BASE_DIR)


def load_asr_backend():
    try:
        return build_asr(CONFIG, BASE_DIR)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "未找到 Vosk 模型目录，请将模型解压至 models/vosk-model-cn 后重试。详见 README_WEB.md。"
        ) from exc
    except RuntimeError as exc:  # faster-whisper missing etc.
        raise


@st.cache_resource(show_spinner=False)
def get_destroyer_cached():
    return build_destroyer(CONFIG, BASE_DIR)


def list_audio_files() -> List[Path]:
    audio_dir = BASE_DIR / CONFIG["paths"]["audio_dir"]
    return sorted(audio_dir.glob("*.wav"))


def save_uploaded_audios(files: Iterable) -> List[Path]:
    saved: List[Path] = []
    audio_dir = BASE_DIR / CONFIG["paths"]["audio_dir"]
    for upl in files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
        target = audio_dir / f"{timestamp}_{upl.name}"
        with target.open("wb") as fh:
            fh.write(upl.getbuffer())
        saved.append(target)
    return saved


def transcribe_audio(files: List[Path]) -> Dict[str, Optional[Path]]:
    if not files:
        raise ValueError("请至少选择一个音频文件。")
    backend = load_asr_backend()
    transcript_text = backend.transcribe_files(files)
    if not transcript_text.strip():
        raise ValueError("转写结果为空，请检查录音文件质量。")

    transcript_dir = BASE_DIR / CONFIG["paths"]["transcript_dir"]
    transcript_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    transcript_path = transcript_dir / f"trans_{timestamp}.txt"
    transcript_path.write_text(transcript_text, encoding="utf-8")

    summary_builder = get_summary_builder()
    proof_path = summary_builder.generate_proofreading_summary(
        transcript_text, CONFIG["summary"]["proofreading_prefix"]
    )

    diff_path: Optional[Path] = None
    quick_path = BASE_DIR / CONFIG["paths"]["summary_dir"] / CONFIG["summary"]["quick_filename"]
    if quick_path.exists():
        diff_path = summary_builder.generate_diff_report(
            quick_path.read_text(encoding="utf-8"),
            proof_path.read_text(encoding="utf-8"),
            CONFIG["summary"]["diff_prefix"],
        )

    return {
        "transcript": transcript_path,
        "proof": proof_path,
        "diff": diff_path,
        "text": transcript_text,
    }


def get_latest_file(directory: Path, prefix: str) -> Optional[Path]:
    candidates = sorted(directory.glob(f"{prefix}*.md"))
    return candidates[-1] if candidates else None


def read_action_items() -> List[Dict[str, str]]:
    path = BASE_DIR / CONFIG["paths"]["summary_dir"] / CONFIG["summary"]["action_items_filename"]
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def render_action_items(actions: List[Dict[str, str]]) -> None:
    if not actions:
        st.info("暂无行动项。")
        return
    for item in actions:
        who = item.get("who", "")
        what = item.get("what", "")
        when = item.get("when", "")
        st.markdown(f"- **{who}**：{what}（完成时限：{when}）")


def render_policy_results(results: List[Dict[str, str]]) -> None:
    if not results:
        st.info("未匹配到制度条款。")
        return
    for idx, item in enumerate(results, start=1):
        st.markdown(f"**{idx}. {item.get('title', '')} / {item.get('section', '')}**")
        st.markdown(f"来源：{item.get('source', '')}")
        st.markdown(f"提示：{item.get('snippet', '').replace('[', '').replace(']', '')}")
        st.markdown("---")


def main() -> None:
    st.set_page_config(page_title="Offline Meeting Records Web", layout="wide")
    st.title("Offline Meeting Records · 本地离线 Web 界面")
    st.caption("离线运行 · 本地存储 · 制度提示仅供参考，不构成合规结论")

    model_dir = BASE_DIR / CONFIG["asr"]["model_path"]
    if not model_dir.exists():
        st.warning(
            "未检测到 Vosk 中文模型目录，请将模型解压至 models/vosk-model-cn/ 后重试。详见 README_WEB.md。"
        )

    tabs = st.tabs([
        "快速版纪要",
        "录音转写校对",
        "政策导入与对照",
        "导出纪要",
        "一键销毁",
    ])

    summary_builder = get_summary_builder()
    summary_dir = BASE_DIR / CONFIG["paths"]["summary_dir"]

    with tabs[0]:
        st.subheader("快速版纪要")
        notes_input = st.text_area("请输入会议要点（每行一条）", height=200)
        if st.button("生成快速版", key="quick_generate"):
            notes = [line.strip() for line in notes_input.splitlines() if line.strip()]
            if not notes:
                st.warning("请至少输入一条要点。")
            else:
                output_path = summary_builder.generate_quick_summary(
                    notes, CONFIG["summary"]["quick_filename"]
                )
                st.success(f"快速版已生成：{output_path.relative_to(BASE_DIR)}")
                actions = read_action_items()
                st.markdown("### 行动项")
                render_action_items(actions)
                st.session_state["latest_quick_path"] = output_path

        quick_path = summary_dir / CONFIG["summary"]["quick_filename"]
        if quick_path.exists():
            st.markdown("#### 最近一次快速版纪要预览")
            st.code(quick_path.read_text(encoding="utf-8"), language="markdown")

    with tabs[1]:
        st.subheader("录音上传与离线转写")
        uploaded_files = st.file_uploader(
            "上传 WAV 录音文件（16kHz 单声道）", type=["wav"], accept_multiple_files=True
        )
        if uploaded_files:
            saved_paths = save_uploaded_audios(uploaded_files)
            if saved_paths:
                st.success("已保存上传音频：" + ", ".join(p.name for p in saved_paths))

        existing_audios = list_audio_files()
        audio_map = {p.name: p for p in existing_audios}
        selection = st.multiselect("选择需转写的音频", list(audio_map.keys()))
        selected_paths = [audio_map[name] for name in selection if name in audio_map]

        if st.button("执行离线转写", key="transcribe_button"):
            try:
                results = transcribe_audio(selected_paths)
            except Exception as exc:  # pylint: disable=broad-except
                st.error(str(exc))
            else:
                st.success("转写完成，已生成校对摘要与差异报告。")
                st.session_state["latest_transcript"] = results["transcript"]
                st.session_state["latest_proof"] = results["proof"]
                if results.get("diff"):
                    st.session_state["latest_diff"] = results["diff"]
                st.text_area("转写文本预览", results["text"], height=200)

        if existing_audios:
            st.markdown("#### 已保存音频文件")
            for path in existing_audios:
                st.markdown(f"- {path.name}")
        else:
            st.info("audio_in/ 目录为空，可通过上方上传录音。")

    with tabs[2]:
        st.subheader("制度导入与对照")
        policy_db = get_policy_database()
        policy_source_dir = BASE_DIR / CONFIG["paths"]["policy_source_dir"]
        if st.button("导入政策库", key="import_policy"):
            sources = [
                p
                for p in policy_source_dir.glob("**/*")
                if p.suffix.lower() in {".pdf", ".docx"}
            ]
            if not sources:
                st.warning("未检测到 PDF 或 Word 制度文件，将跳过导入。")
            else:
                count = policy_db.import_sources()
                errors = policy_db.pop_last_errors()
                if errors:
                    st.warning(
                        "部分制度文件导入失败（已跳过）：\n" + "\n".join(errors[:5])
                        + ("\n……" if len(errors) > 5 else "")
                    )
                st.success(f"导入完成，共 {count} 条制度条款。")

        summary_options: Dict[str, Path] = {}
        if quick_path.exists():
            summary_options["快速版纪要"] = quick_path
        latest_proof = get_latest_file(summary_dir, CONFIG["summary"]["proofreading_prefix"])
        if latest_proof:
            summary_options[f"录音校对摘要（{latest_proof.stem}）"] = latest_proof

        selected_option = None
        if summary_options:
            label = st.selectbox("选择摘要作为检索依据", list(summary_options.keys()))
            selected_option = summary_options[label]
        manual_query = st.text_area("或输入自定义检索关键词", height=120)

        if st.button("执行制度检索", key="policy_search"):
            query_text = ""
            if selected_option and selected_option.exists():
                content = selected_option.read_text(encoding="utf-8")
                bullets = [
                    line.strip("- ").strip()
                    for line in content.splitlines()
                    if line.startswith("-")
                ]
                query_text = " ".join(bullets)
            if manual_query.strip():
                query_text = f"{query_text} {manual_query.strip()}".strip()
            if not query_text:
                st.warning("请先生成摘要或输入检索关键词。")
            else:
                results = policy_db.search(query_text)
                st.session_state["policy_results"] = results
                render_policy_results(results)

        if "policy_results" in st.session_state:
            st.markdown("#### 最近的制度提示")
            render_policy_results(st.session_state.get("policy_results", []))
        else:
            st.info("暂未执行检索。")

    with tabs[3]:
        st.subheader("导出纪要 Docx")
        col1, col2 = st.columns(2)
        with col1:
            meeting_title = st.text_input("纪要标题", value="Offline Meeting 会议纪要")
            topic = st.text_input("会议主题")
            host = st.text_input("主持人")
            participants = st.text_area("与会人员", height=80)
        with col2:
            time_place = st.text_input("时间地点")
            recorder = st.text_input("记录人")
            template_name = st.selectbox(
                "导出模板",
                list(TEMPLATE_PRESETS.keys()),
                index=list(TEMPLATE_PRESETS.keys()).index(CONFIG["summary"].get("default_template", "通用"))
                if CONFIG["summary"].get("default_template", "通用") in TEMPLATE_PRESETS
                else 0,
            )

        available_summary_files: List[Path] = []
        if quick_path.exists():
            available_summary_files.append(quick_path)
        latest_proof = get_latest_file(summary_dir, CONFIG["summary"]["proofreading_prefix"])
        if latest_proof and latest_proof not in available_summary_files:
            available_summary_files.append(latest_proof)

        summary_labels = [
            "快速版纪要" if path == quick_path else f"录音校对摘要（{path.name})"
            for path in available_summary_files
        ]
        selected_summary_idx = 0
        if available_summary_files:
            selected_summary_idx = st.selectbox(
                "选择用于导出的摘要",
                range(len(available_summary_files)),
                format_func=lambda idx: summary_labels[idx],
            )
        else:
            st.warning("尚未生成任何摘要，请先完成快速版或录音校对。")

        include_minutes = st.checkbox("同时覆盖删除 minutes/（默认保留）", value=False, disabled=True)
        if include_minutes:
            st.info("Web 版本默认保留 minutes/ 目录，需在一键销毁页手动选择。")

        if st.button("导出纪要", key="export_minutes"):
            if not available_summary_files:
                st.error("请先生成摘要内容。")
            else:
                summary_path = available_summary_files[selected_summary_idx]
                summary_text = summary_path.read_text(encoding="utf-8")
                if summary_path.name.startswith(CONFIG["summary"]["proofreading_prefix"]):
                    summary_title = "录音校对定稿"
                else:
                    summary_title = "快速版纪要"

                diff_path = get_latest_file(summary_dir, CONFIG["summary"]["diff_prefix"])
                diff_content = (
                    diff_path.read_text(encoding="utf-8") if diff_path and diff_path.exists() else None
                )
                actions = read_action_items()
                policy_results = st.session_state.get("policy_results", [])

                meeting_info = {
                    "title": meeting_title,
                    "topic": topic,
                    "time_place": time_place,
                    "host": host,
                    "recorder": recorder,
                    "participants": participants,
                }
                minutes_dir = BASE_DIR / CONFIG["paths"]["minutes_dir"]
                minutes_dir.mkdir(parents=True, exist_ok=True)
                output_path = minutes_dir / f"minutes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                create_minutes_document(
                    output_path=output_path,
                    meeting_info=meeting_info,
                    summary_title=summary_title,
                    summary_content=summary_text,
                    diff_content=diff_content,
                    action_items=actions,
                    policy_suggestions=policy_results,
                    template_name=template_name,
                )
                st.success(f"纪要已导出：{output_path.relative_to(BASE_DIR)}")
                with output_path.open("rb") as fh:
                    st.download_button(
                        label="下载纪要 Docx",
                        data=fh.read(),
                        file_name=output_path.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

    with tabs[4]:
        st.subheader("一键销毁")
        st.caption("默认保留 minutes/ 目录，可选覆盖删除。SDelete 缺失时将降级为普通删除并提示。")
        include_minutes = st.checkbox("同时删除 minutes/", value=False)
        if st.button("执行一键销毁", key="destroy_button"):
            destroyer = get_destroyer_cached()
            result = destroyer.destroy(include_minutes=include_minutes)
            removed = result.get("results", [])
            st.markdown("#### 已清理目录")
            for item in removed:
                raw_path = getattr(item, "path", None)
                if raw_path is None:
                    continue
                path_obj = Path(raw_path)
                try:
                    display_path = path_obj.relative_to(BASE_DIR)
                except ValueError:
                    display_path = path_obj
                mode = getattr(item, "mode", "")
                existed = getattr(item, "existed", False)
                status = "已清理" if existed else "原本为空"
                st.markdown(f"- {display_path} → {status}（模式：{mode}）")
            if result.get("fallback_used"):
                st.warning(result.get("message") or "已使用普通删除，建议启用磁盘加密。")
            else:
                st.success("全部目标目录已处理。")


if __name__ == "__main__":
    main()
