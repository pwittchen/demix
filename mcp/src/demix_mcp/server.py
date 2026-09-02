"""FastMCP server exposing demix audio-processing tools.

The server shells out to the `demix` CLI; it does not import demix's
Python modules. This decouples the MCP server's Python environment
(3.10+, for the `mcp` SDK) from demix's own (3.8, for spleeter).

Tools exposed:
  - process_audio: download/search/process a song with optional stem
                   separation, tempo, transpose, key targeting, cutting.
  - detect_key:    detect musical key of a local audio file.
  - search_youtube: resolve a search query to a YouTube URL + title.
  - clean:         remove demix output and/or cached spleeter models.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal, Optional

try:
    # mcp SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # pragma: no cover - depends on installed SDK
    # mcp SDK 1.x, where the same class was called FastMCP
    from mcp.server.fastmcp import FastMCP as _Server


mcp = _Server("demix")


VALID_MODES = ("nosplit", "2stems", "4stems", "5stems")
STEM_FILES = {
    "nosplit": [],
    "2stems": ["vocals", "accompaniment"],
    "4stems": ["vocals", "drums", "bass", "other"],
    "5stems": ["vocals", "drums", "bass", "piano", "other"],
}

# Matches: "Detected key: C major (confidence: 87%)" with optional ANSI codes
# and an optional "(after transpose)" label.
_KEY_LINE_RE = re.compile(
    r"Detected key(?:\s+\(([^)]+)\))?:\s+([A-G][#b]?)\s+(major|minor)\s+"
    r"\(confidence:\s+(\d+)%\)"
)


def _demix_bin() -> str:
    """Locate the demix CLI binary, raising a clear error if missing."""
    path = shutil.which("demix")
    if path is None:
        raise RuntimeError(
            "demix CLI not found on PATH. Install it in a Python 3.8 "
            "environment (e.g. `pipx install demix`) and ensure the "
            "`demix` command is reachable from the MCP server's PATH."
        )
    return path


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _resolve_output_dir(output_dir: str, cwd: Optional[str]) -> Path:
    base = Path(cwd).expanduser() if cwd else Path.cwd()
    out = Path(output_dir).expanduser()
    return out if out.is_absolute() else base / out


def _list_output_files(output_dir: Path) -> dict:
    """Return a flat mapping of stem-name -> absolute file path under output/."""
    if not output_dir.exists():
        return {}
    files: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            rel = path.relative_to(output_dir).as_posix()
            files[rel] = str(path.resolve())
    return files


@mcp.tool()
def process_audio(
    file: Optional[str] = None,
    url: Optional[str] = None,
    search: Optional[str] = None,
    mode: Literal["nosplit", "2stems", "4stems", "5stems"] = "nosplit",
    output_dir: str = "output",
    tempo: float = 1.0,
    transpose: int = 0,
    target_key: Optional[str] = None,
    detect_key: bool = False,
    start: Optional[str] = None,
    end: Optional[str] = None,
    video: bool = False,
    cwd: Optional[str] = None,
) -> dict:
    """Process an audio source with demix: download/load, optionally cut,
    separate stems, adjust tempo/pitch, transpose to a target key.

    Provide exactly one of `file`, `url`, or `search`.

    Args:
        file: Local audio file path (mp3/wav/flac/...).
        url: YouTube video URL.
        search: YouTube search query (e.g. "Queen - Bohemian Rhapsody").
        mode: Stem separation mode. "nosplit" only converts/applies effects.
        output_dir: Output directory (relative to cwd or absolute).
        tempo: Tempo factor (e.g. 0.8 = 80% speed). Range typically 0.5-2.0.
        transpose: Pitch shift in semitones (-12 to +12). Cannot combine
            with target_key.
        target_key: Target musical key like "C", "Am", "F# minor". Auto-
            detects current key and computes transposition.
        detect_key: When true, prints the detected musical key.
        start: Cut start time, "MM:SS" or "HH:MM:SS".
        end: Cut end time, "MM:SS" or "HH:MM:SS".
        video: Generate an .mkv video for the output (accompaniment in
            2stems mode, full music in nosplit mode).
        cwd: Working directory for the demix process (defaults to MCP
            server's cwd). Spleeter models are cached here in
            pretrained_models/, so a stable directory is recommended.

    Returns:
        dict with: ok, command, stdout, stderr, exit_code, output_dir,
        files (mapping of relative path -> absolute path).
    """
    sources = [s for s in (file, url, search) if s]
    if len(sources) != 1:
        return {
            "ok": False,
            "error": "Provide exactly one of `file`, `url`, or `search`.",
        }
    if mode not in VALID_MODES:
        return {"ok": False, "error": f"Invalid mode: {mode}"}
    if target_key and transpose != 0:
        return {
            "ok": False,
            "error": "`target_key` and `transpose` cannot be combined.",
        }
    if file and not Path(file).expanduser().is_file():
        return {"ok": False, "error": f"File not found: {file}"}

    abs_output = _resolve_output_dir(output_dir, cwd)

    cmd: list[str] = [_demix_bin()]
    if file:
        cmd += ["-f", str(Path(file).expanduser())]
    elif url:
        cmd += ["-u", url]
    else:
        cmd += ["-s", search]  # type: ignore[list-item]
    cmd += ["-m", mode, "-o", str(abs_output)]
    if tempo != 1.0:
        cmd += ["-t", str(tempo)]
    if transpose != 0:
        cmd += ["-p", str(transpose)]
    if target_key:
        cmd += ["-K", target_key]
    if detect_key:
        cmd += ["-k"]
    if start:
        cmd += ["-ss", start]
    if end:
        cmd += ["-to", end]
    if video:
        cmd += ["--video"]

    run_cwd = str(Path(cwd).expanduser()) if cwd else None
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=run_cwd)

    result = {
        "ok": proc.returncode == 0,
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout": _strip_ansi(proc.stdout),
        "stderr": _strip_ansi(proc.stderr),
        "output_dir": str(abs_output),
        "files": _list_output_files(abs_output),
    }
    return result


@mcp.tool()
def detect_key(file: str) -> dict:
    """Detect the musical key of a local audio file.

    Runs demix in nosplit mode against a temporary output directory so the
    user's existing output/ is not affected. The audio is converted to WAV
    once for analysis and discarded.

    Args:
        file: Path to a local audio file (mp3/wav/flac/...).

    Returns:
        dict with: ok, key (e.g. "C"), scale ("major"|"minor"),
        confidence (0-100), and raw stdout/stderr on failure.
    """
    audio_path = Path(file).expanduser()
    if not audio_path.is_file():
        return {"ok": False, "error": f"File not found: {file}"}

    with tempfile.TemporaryDirectory(prefix="demix-mcp-") as tmp:
        cmd = [
            _demix_bin(),
            "-f", str(audio_path),
            "-k",
            "-m", "nosplit",
            "-o", tmp,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        return {
            "ok": False,
            "error": "demix exited with non-zero status",
            "exit_code": proc.returncode,
            "stdout": _strip_ansi(proc.stdout),
            "stderr": _strip_ansi(proc.stderr),
        }

    text = _strip_ansi(proc.stdout)
    match = _KEY_LINE_RE.search(text)
    if not match:
        return {
            "ok": False,
            "error": "Could not parse key from demix output",
            "stdout": text,
        }

    _label, key, scale, confidence = match.groups()
    return {
        "ok": True,
        "key": key,
        "scale": scale,
        "confidence": int(confidence),
    }


@mcp.tool()
def search_youtube(query: str) -> dict:
    """Resolve a YouTube search query to its top result URL and title.

    Uses yt-dlp directly (the same tool demix prefers internally) so this
    works without doing a full audio-processing run.

    Args:
        query: Search string, e.g. "Queen Bohemian Rhapsody".

    Returns:
        dict with: ok, url, title, video_id. On failure: error message.
    """
    if shutil.which("yt-dlp") is None:
        return {
            "ok": False,
            "error": "yt-dlp not found on PATH. Install with "
                     "`brew install yt-dlp` or `pipx install yt-dlp`.",
        }

    proc = subprocess.run(
        ["yt-dlp", f"ytsearch1:{query}", "--dump-json", "--no-download"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return {
            "ok": False,
            "error": "No results found",
            "stderr": proc.stderr.strip(),
        }

    info = json.loads(proc.stdout.splitlines()[0])
    video_id = info.get("id", "")
    return {
        "ok": True,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": info.get("title"),
        "video_id": video_id,
    }


@mcp.tool()
def clean(
    target: Literal["output", "models", "all"] = "output",
    output_dir: str = "output",
    cwd: Optional[str] = None,
) -> dict:
    """Remove demix output files and/or cached spleeter models.

    Args:
        target: "output" removes the output directory; "models" removes
            cached pretrained_models/; "all" removes both.
        output_dir: Output directory to clean (relevant for "output"/"all").
        cwd: Working directory for the demix process. "models" is resolved
            relative to this directory (it lives in pretrained_models/).

    Returns:
        dict with: ok, command, exit_code, stdout, stderr.
    """
    abs_output = _resolve_output_dir(output_dir, cwd)
    cmd = [_demix_bin(), "-c", target, "-o", str(abs_output)]
    run_cwd = str(Path(cwd).expanduser()) if cwd else None
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=run_cwd)
    return {
        "ok": proc.returncode == 0,
        "command": cmd,
        "exit_code": proc.returncode,
        "stdout": _strip_ansi(proc.stdout),
        "stderr": _strip_ansi(proc.stderr),
    }


def main() -> None:
    """Entry point for the `demix-mcp` console script (stdio transport)."""
    # Surface a friendly startup error if the demix CLI is missing rather
    # than failing on the first tool call.
    if shutil.which("demix") is None:
        print(
            "warning: `demix` CLI not found on PATH. Tools will fail until "
            "demix is installed and reachable.",
            file=sys.stderr,
        )
    mcp.run()


if __name__ == "__main__":
    main()
