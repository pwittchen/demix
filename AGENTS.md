# Repository Guidelines

## Project Structure & Modules
- Core CLI implementation: `src/demix/cli.py` handles argument parsing, YouTube search/download, audio ingest, FFmpeg conversions, key detection/transposition, Spleeter stem separation, and output assembly.
- Package entrypoints: `src/demix/__init__.py` exports public API/version; root `demix.py` is a backwards-compatible wrapper for `python demix.py` usage.
- Tests: `tests/test_demix.py` (pytest + unittest.mock) covers argument parsing, helpers, and workflow wiring; add new tests here.
- Assets/output: `output/` (contains `music/wav/` for music.wav and separated stems as wav, `music/mp3/` for music.mp3 and separated stems as mp3, `video/` for downloads and accompaniment video; cleaned by `--clean output`), `pretrained_models/` (downloaded once by Spleeter, can be wiped with `--clean models`).
- Build/runtime config: `pyproject.toml` (package metadata, entrypoint, pytest/flake8 config), `requirements.txt` (runtime deps), `README.md` (setup/usage), `CLAUDE.md` (project notes).

## Build, Test, and Development
- Create env (example): `mkvirtualenv -p /Users/pw/.pyenv/versions/3.8.16/bin/python demix && workon demix`.
- Install deps: `pip install -r requirements.txt` (needs FFmpeg installed on PATH).
- Run CLI locally:
  - Installed entrypoint: `demix -u "https://youtu.be/ID" -m 4stems -o output`
  - Development wrapper: `python demix.py -u "https://youtu.be/ID" -m 4stems -o output`
  - YouTube search: `demix -s "Artist - Song Name" -m 4stems`
  - Local file: `demix -f /path/to/song.wav -ss 0:30 -to 2:00 -t 0.9 -p -2`
- Tests: `pytest -v` (unit-level, no network/FFmpeg execution due to mocking).
- Lint (CI style): `flake8 . --max-complexity=10 --max-line-length=127`.

## Coding Style & Naming
- Python `>=3.8,<3.9`, 4-space indentation, prefer stdlib + installed deps (pytubefix, spleeter, ffmpeg bindings, essentia).
- Keep CLI args consistent with `argparse` setup in `parse_args` (`src/demix/cli.py`); reuse existing help text style.
- Functions are lowercase_with_underscores; constants ALL_CAPS. Keep side-effecting helpers small and composable.
- Suppress noisy subprocess output (stdout/stderr) unless explicitly needed.

## Testing Guidelines
- Add pytest coverage for new flags, edge cases, and error paths; mock heavy calls (`subprocess`, `YouTube`, filesystem) similar to existing tests.
- Use realistic sample arguments in `patch.object(sys, "argv", [...])`.
- When changing command construction, assert positional ordering in tests (e.g., `-ss` before `-i`).

## Keeping Docs in Sync
- If you change user-facing CLI behavior in `src/demix/cli.py`, update `README.md` in the same change.
- Keep these in sync with CLI changes: options/flags, defaults, modes, output layout, usage examples, and dependencies.
- If dependencies change, update both `requirements.txt` and `pyproject.toml`.

## Commit & Pull Request Guidelines
- Follow recent history: short, imperative subject lines; reference issues with `closes #ID` when applicable (see `git log --oneline`).
- PRs should describe behavior changes, include sample CLI invocations, note test coverage, and call out any new external requirements (models, FFmpeg versions).
- If output format or directory layout changes, mention migration/cleanup steps (e.g., rerun with `--clean all`).

## Operational & Safety Notes
- Ensure `ffmpeg` and `ffprobe` are available before running (use `which ffmpeg`).
- Large model downloads occur on first separation; avoid committing `pretrained_models/` or `output/`.
- Prefer local testing; avoid network calls in tests and keep subprocesses mocked to prevent long runs.
