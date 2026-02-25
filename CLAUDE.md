# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

demix is a Python CLI tool that separates audio from songs into individual stems (vocals, instruments) using AI-powered audio processing. It can search YouTube by artist/song name, download from YouTube URL, or process local audio files, apply tempo/pitch adjustments, detect and transpose musical key, and cut audio segments.

## Development Commands

```bash
# Setup environment (requires Python 3.8, ffmpeg installed via homebrew or similar)
mkvirtualenv -p /path/to/python3.8 demix
workon demix
pip install -r requirements.txt

# Run tests
pip install pytest
pytest -v                    # all tests
pytest -v -k test_name       # specific test

# Lint (as used in CI)
flake8 . --max-complexity=10 --max-line-length=127

# Run the tool (installed via pip)
demix -u <youtube-url> [options]
demix -s <search-query> [options]
demix -f <audio-file> [options]

# Or run directly for development
python demix.py -u <youtube-url> [options]
```

## Architecture

**Package structure**: The application lives in `src/demix/` with `cli.py` (~745 lines) as the main module and `__init__.py` for package exports. The root `demix.py` is a backwards-compatible wrapper. Build configuration is in `pyproject.toml`.

```
src/demix/
├── __init__.py    # Package exports and version
├── cli.py         # All CLI logic, processing functions
demix.py           # Backwards-compatible wrapper
pyproject.toml     # Build config, dependencies, entry point
```

The application orchestrates four external tools:

1. **pytubefix** - YouTube search and downloads
2. **FFmpeg** - Audio/video conversion and effects (subprocess calls)
3. **Spleeter** - AI audio separation (subprocess calls to CLI)
4. **Essentia** - Musical key detection

**Processing pipeline**: search (optional) → download → convert to WAV → detect/transpose key (optional) → separate with Spleeter (optional) → apply effects (tempo/pitch) → convert to MP3 → output

**Output structure**:
```
output/
├── music/
│   ├── wav/       # music.wav + separated stems as wav files
│   └── mp3/       # music.mp3 + separated stems as mp3 files
├── video/         # Downloaded video and accompaniment video container
pretrained_models/ # Cached Spleeter models (~300MB, downloads on first run)
```

**Key design patterns**:
- All heavy operations run as subprocesses with suppressed output
- `Spinner` class provides threaded terminal progress indication (supports context manager)
- Effects (tempo/pitch) are chained FFmpeg filters (asetrate/aresample for pitch, atempo for tempo)
- Spleeter models lazy-load on first separation
- Key detection uses Essentia's `KeyExtractor` algorithm

## Processing Modes

- `nosplit`: no stem separation — download, convert, and apply effects only (default)
- `2stems`: vocals, accompaniment
- `4stems`: vocals, drums, bass, other
- `5stems`: vocals, drums, bass, piano, other

## Dependencies

System: ffmpeg, ffprobe (checked at runtime)
Python: pytubefix, ffmpeg (bindings), spleeter, essentia

## Keeping Documentation in Sync

**IMPORTANT**: When making any user-facing changes to the CLI application (`src/demix/cli.py`), you MUST also update `README.md` to reflect those changes. This includes but is not limited to:

- Adding, removing, or renaming CLI options/flags
- Changing default values for existing options
- Adding new processing modes or removing existing ones
- Changing the output directory structure
- Adding new features or capabilities
- Changing usage examples or workflows
- Updating dependencies (also update `requirements.txt` and `pyproject.toml`)
