"""Faster-Whisper based offline transcription backend."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from faster_whisper import WhisperModel  # type: ignore


class FasterWhisperASRModel:
    """Run faster-whisper locally with optional GPU acceleration."""

    def __init__(
        self,
        model_path: Path,
        compute_type: str = "auto",
        vad_filter: bool = True,
        beam_size: int = 5,
    ) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"未找到 faster-whisper 模型目录: {model_path}")
        self.model = WhisperModel(str(model_path), device="auto", compute_type=compute_type)
        self.vad_filter = vad_filter
        self.beam_size = beam_size

    def transcribe_files(self, audio_files: Iterable[Path]) -> str:
        """Transcribe one or more audio files and return concatenated text."""

        transcripts: List[str] = []
        for audio in audio_files:
            if not audio.exists():
                continue
            segments, _ = self.model.transcribe(
                str(audio),
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
                language="zh",
            )
            parts: List[str] = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    parts.append(text)
            if parts:
                transcripts.append(" ".join(parts))
        return "\n".join(transcripts)
