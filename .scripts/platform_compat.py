#!/usr/bin/env python3
"""Shared host adapters for deterministic Word extraction and rendering."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Callable, Mapping

Which = Callable[[str], str | None]


def _executable(path: str | Path | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path).expanduser()
    if candidate.is_file() and os.access(candidate, os.X_OK):
        # Keep launcher symlinks intact. Snap dispatches from the invoked name,
        # so resolving /snap/bin/libreoffice to /usr/bin/snap breaks argv[0].
        return candidate.absolute()
    return None



def find_executable(*names: str, which: Which = shutil.which) -> Path | None:
    """Return the first executable resolved from ``PATH``."""
    for name in names:
        resolved = _executable(which(name))
        if resolved is not None:
            return resolved
    return None



def find_soffice(
    explicit: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    which: Which = shutil.which,
    home: Path | None = None,
) -> Path | None:
    """Resolve LibreOffice on Ubuntu, packaged runtimes, and macOS."""
    environment = os.environ if environ is None else environ
    candidates: list[Path] = []
    for configured in (explicit, environment.get("SOFFICE_BIN")):
        if configured:
            candidates.append(Path(configured).expanduser())

    for name in ("soffice", "libreoffice"):
        found = which(name)
        if found:
            candidates.append(Path(found))

    candidates.extend([
        Path("/usr/lib/libreoffice/program/soffice"),
        Path("/snap/bin/libreoffice"),
        Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    ])
    runtime_root = (home or Path.home()) / ".cache" / "codex-runtimes"
    if runtime_root.exists():
        candidates.extend(sorted(
            runtime_root.glob("*/dependencies/bin/override/soffice"),
            reverse=True,
        ))

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        resolved = _executable(candidate)
        if resolved is not None:
            return resolved
    return None



def default_cjk_font(
    *,
    mac_default: str = "Heiti SC",
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return the explicit or platform-native default CJK font family."""
    environment = os.environ if environ is None else environ
    configured = str(environment.get("ASKS_CJK_FONT", "")).strip()
    if configured:
        return configured
    host = platform or sys.platform
    if host == "darwin":
        return mac_default
    if host.startswith("win"):
        return "Microsoft YaHei"
    return "Noto Sans CJK SC"



def soffice_environment(
    soffice: str | Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build a child environment without mutating the caller's environment."""
    env = dict(os.environ if environ is None else environ)
    if env.get("FONTCONFIG_FILE") or env.get("FONTCONFIG_PATH"):
        return env

    binary = Path(soffice)
    binaries = [binary]
    try:
        resolved_binary = binary.resolve(strict=True)
    except OSError:
        resolved_binary = binary
    if resolved_binary != binary:
        binaries.append(resolved_binary)

    candidates: list[Path] = []
    for candidate_binary in binaries:
        candidates.append(
            candidate_binary.parent.parent / "Resources/fontconfig/fonts.conf"
        )
        if (
            candidate_binary.parent.name == "override"
            and candidate_binary.parent.parent.name == "bin"
        ):
            candidates.append(
                candidate_binary.parent.parent.parent
                / "native/libreoffice-headless/libreoffice/LibreOfficeDev.app"
                / "Contents/Resources/fontconfig/fonts.conf"
            )
    for config in candidates:
        if config.is_file():
            env["FONTCONFIG_FILE"] = str(config)
            break
    return env

