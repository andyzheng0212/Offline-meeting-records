"""Recorder module for Offline Meeting Records.

Provides high level APIs to manage audio recording sessions with
sounddevice. Audio is chunked into WAV files to reduce data loss.
Markers are collected during recording and saved to JSON when stopped.
"""
from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np
import sounddevice as sd
import soundfile as sf


@dataclass
class RecorderConfig:
    """Configuration values loaded from config.yaml."""

    sample_rate: int
    channels: int
    chunk_seconds: int
    device: Optional[int]
    audio_dir: Path
    markers_dir: Path


@dataclass
class Marker:
    """A time anchored marker raised during recording."""

    timestamp: float
    label: str


class RecorderError(RuntimeError):
    """Custom error for recorder module."""


class AudioRecorder:
    """Manage audio recording session with background writing thread."""

    def __init__(self, config: RecorderConfig) -> None:
        self.config = config
        self._queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._writer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._session_id: Optional[str] = None
        self._start_time: Optional[float] = None
        self._markers: List[Marker] = []
        self._current_file: Optional[sf.SoundFile] = None
        self._file_index = 0
        self.config.audio_dir.mkdir(parents=True, exist_ok=True)
        self.config.markers_dir.mkdir(parents=True, exist_ok=True)

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    def start(self) -> str:
        """Start a new recording session."""

        if self._stream is not None:
            raise RecorderError("录音已经在进行中。")

        session_id = time.strftime("%Y%m%d_%H%M%S")
        self._session_id = session_id
        self._start_time = time.time()
        self._markers = []
        self._file_index = 0
        self._stop_event.clear()

        def callback(indata, frames, time_info, status):  # type: ignore[override]
            if status:
                print(f"[Recorder] Input stream status: {status}")
            self._queue.put(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype="float32",
            callback=callback,
            device=self.config.device,
        )
        self._stream.start()

        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer_thread.start()
        return session_id

    def _next_file(self) -> sf.SoundFile:
        if self._session_id is None:
            raise RecorderError("会话尚未开始。")
        self._file_index += 1
        filename = f"{self._session_id}_part{self._file_index:02d}.wav"
        file_path = self.config.audio_dir / filename
        return sf.SoundFile(
            file_path,
            mode="w",
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            subtype="PCM_16",
        )

    def _writer_loop(self) -> None:
        chunk_frames = self.config.chunk_seconds * self.config.sample_rate
        frames_written = 0
        current_file = self._next_file()
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                data = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            offset = 0
            while offset < len(data):
                remaining_in_chunk = chunk_frames - frames_written
                take = min(len(data) - offset, remaining_in_chunk)
                current_file.write(data[offset : offset + take])
                frames_written += take
                offset += take
                if frames_written >= chunk_frames:
                    current_file.close()
                    frames_written = 0
                    current_file = self._next_file()
        current_file.close()

    def mark(self, label: str) -> None:
        """Insert a marker at the current timestamp."""

        if self._stream is None or self._start_time is None:
            raise RecorderError("录音尚未开始，无法标记。")
        timestamp = time.time() - self._start_time
        self._markers.append(Marker(timestamp=timestamp, label=label))

    def stop(self) -> Path:
        """Stop current recording session and persist markers."""

        if self._stream is None:
            raise RecorderError("当前没有进行中的录音。")

        self._stop_event.set()
        self._stream.stop()
        self._stream.close()
        self._stream = None
        if self._writer_thread:
            self._writer_thread.join()
        self._writer_thread = None

        markers_path = self._save_markers()
        self._session_id = None
        self._start_time = None
        self._queue = queue.Queue()
        return markers_path

    def _save_markers(self) -> Path:
        if self._session_id is None:
            raise RecorderError("会话尚未开始。")
        markers_file = self.config.markers_dir / f"markers_{self._session_id}.json"
        markers_data = [marker.__dict__ for marker in self._markers]
        with markers_file.open("w", encoding="utf-8") as f:
            json.dump(markers_data, f, ensure_ascii=False, indent=2)
        return markers_file


def build_recorder(config: dict, base_path: Path) -> AudioRecorder:
    """Factory function to create recorder from config dictionary."""

    paths = config["paths"]
    recording = config["recording"]
    recorder_config = RecorderConfig(
        sample_rate=recording["sample_rate"],
        channels=recording["channels"],
        chunk_seconds=recording["chunk_seconds"],
        device=recording.get("device"),
        audio_dir=base_path / paths["audio_dir"],
        markers_dir=base_path / paths["markers_dir"],
    )
    return AudioRecorder(recorder_config)
