"""Secure destruction utilities for sensitive artifacts."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class DestroyResult:
    """Represent the result for a single path deletion."""

    path: Path
    mode: str
    existed: bool


class Destroyer:
    """Secure deletion helper that prefers SDelete when available."""

    def __init__(
        self,
        target_dirs: List[Path],
        sdelete_path: Path,
        overwrite_passes: int = 1,
        mode: str = "sdelete",
        fallback_message: str | None = None,
    ) -> None:
        self.target_dirs = target_dirs
        self.sdelete_path = sdelete_path
        self.overwrite_passes = overwrite_passes
        self.mode = mode
        self.fallback_message = fallback_message or "已切换为普通删除。"

    def destroy(self, include_minutes: bool = False) -> Dict[str, object]:
        """Execute secure deletion across configured directories."""

        results: List[DestroyResult] = []
        for directory in self.target_dirs:
            if not include_minutes and directory.name == "minutes":
                continue
            results.append(self._secure_remove(directory))
        fallback_used = self.mode == "sdelete" and any(result.mode == "standard" for result in results)
        return {
            "results": results,
            "fallback_used": fallback_used,
            "message": self.fallback_message if fallback_used else "",
        }

    def _secure_remove(self, path: Path) -> DestroyResult:
        """Remove a path using SDelete when configured, else普通删除."""

        existed = path.exists()
        if not existed:
            return DestroyResult(path=path, mode="skipped", existed=False)

        if self.mode == "sdelete" and self.sdelete_path.exists():
            try:
                self._run_sdelete(path)
                cleanup_mode = "sdelete"
            except subprocess.CalledProcessError:
                self._fallback_remove(path)
                cleanup_mode = "standard"
        else:
            self._fallback_remove(path)
            cleanup_mode = "standard"

        if path.is_dir():
            path.mkdir(parents=True, exist_ok=True)

        return DestroyResult(path=path, mode=cleanup_mode, existed=True)

    def _fallback_remove(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()

    def _run_sdelete(self, path: Path) -> None:
        command = [str(self.sdelete_path), "-p", str(self.overwrite_passes)]
        if path.is_dir():
            command.extend(["-s", str(path)])
        else:
            command.append(str(path))
        subprocess.run(command, check=True)
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()
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
    secure_cfg = config.get("secure_delete", {})
    sdelete_rel = secure_cfg.get("sdelete_path", "bin/sdelete64.exe")
    return Destroyer(
        target_dirs=targets,
        sdelete_path=base_path / sdelete_rel,
        overwrite_passes=secure_cfg.get("overwrite_passes", 1),
        mode=secure_cfg.get("mode", "sdelete"),
        fallback_message=secure_cfg.get("fallback_message"),
    )
    sdelete_path = base_path / paths["sdelete_path"]
    overwrite_passes = config["security"].get("overwrite_passes", 1)
    return Destroyer(target_dirs=targets, sdelete_path=sdelete_path, overwrite_passes=overwrite_passes)
