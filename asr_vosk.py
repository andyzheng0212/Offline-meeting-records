"""Offline speech recognition using Vosk."""
from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Dict, Iterable, List

from vosk import KaldiRecognizer, Model  # type: ignore


class ASRModel:
    """Wrapper around Vosk model for offline transcription."""

    def __init__(self, model_dir: Path, sample_rate: int, max_alternatives: int = 0, words: bool = True) -> None:
        if not model_dir.exists():
            raise FileNotFoundError(f"未找到 Vosk 模型目录: {model_dir}")
        self.model = Model(str(model_dir))
        self.sample_rate = sample_rate
        self.max_alternatives = max_alternatives
        self.words = words

    def transcribe(self, audio_path: Path) -> Dict:
        """Transcribe a single WAV file and return structured JSON result."""

        with wave.open(str(audio_path), "rb") as wf:
            if wf.getframerate() != self.sample_rate:
                raise ValueError(f"音频采样率 {wf.getframerate()}Hz 与配置 {self.sample_rate}Hz 不一致")
            if wf.getnchannels() != 1:
                raise ValueError("请提供单声道 WAV 音频文件。")
            rec = KaldiRecognizer(self.model, self.sample_rate)
            rec.SetWords(self.words)
            if self.max_alternatives:
                rec.SetMaxAlternatives(self.max_alternatives)
            results: List[Dict] = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    results.append(json.loads(rec.Result()))
            final_result = json.loads(rec.FinalResult())
            if final_result:
                results.append(final_result)
        return {"results": results}

    def transcribe_files(self, audio_files: Iterable[Path]) -> str:
        """Transcribe a collection of audio files and return concatenated text."""

        transcripts: List[str] = []
        for audio in audio_files:
            if not audio.exists():
                continue
            result = self.transcribe(audio)
            fragments = []
            for segment in result["results"]:
                if "text" in segment:
                    fragments.append(segment["text"])
            transcripts.append(" ".join(fragments))
        return "\n".join(transcripts)


def build_asr(config: dict, base_path: Path) -> ASRModel:
    asr_cfg = config["asr"]
    recording_cfg = config["recording"]
    model_path = base_path / asr_cfg["model_path"]
    return ASRModel(
        model_dir=model_path,
        sample_rate=recording_cfg["sample_rate"],
        max_alternatives=asr_cfg.get("max_alternatives", 0),
        words=asr_cfg.get("words", True),
    )
