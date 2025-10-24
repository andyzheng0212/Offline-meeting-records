"""Secure destruction utilities for sensitive artifacts."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List


class Destroyer:
    def __init__(self, target_dirs: List[Path], sdelete_path: Path, overwrite_passes: int = 1) -> None:
        self.target_dirs = target_dirs
        self.sdelete_path = sdelete_path
        self.overwrite_passes = overwrite_passes

    def destroy(self, include_minutes: bool = False) -> None:
        for directory in self.target_dirs:
            if not include_minutes and directory.name == "minutes":
                continue
            self._secure_remove(directory)

    def _secure_remove(self, path: Path) -> None:
        if not path.exists():
            return
        if self.sdelete_path.exists():
            self._run_sdelete(path)
            if path.is_dir():
                path.mkdir(parents=True, exist_ok=True)
        else:
            if path.is_dir():
                shutil.rmtree(path)
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.unlink()

    def _run_sdelete(self, path: Path) -> None:
        command = [
            str(self.sdelete_path),
            "-p",
            str(self.overwrite_passes),
            "-s",
            str(path),
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as exc:
            print(f"SDelete 执行失败，回退到普通删除: {exc}")
            if path.is_dir():
                shutil.rmtree(path)
                path.mkdir(parents=True, exist_ok=True)
            elif path.exists():
                path.unlink()


def build_destroyer(config: dict, base_path: Path) -> Destroyer:
    paths = config["paths"]
    targets = [
        base_path / paths["audio_dir"],
        base_path / paths["markers_dir"],
        base_path / paths["transcript_dir"],
        base_path / paths["summary_dir"],
        base_path / paths["minutes_dir"],
    ]
    sdelete_path = base_path / paths["sdelete_path"]
    overwrite_passes = config["security"].get("overwrite_passes", 1)
    return Destroyer(target_dirs=targets, sdelete_path=sdelete_path, overwrite_passes=overwrite_passes)
