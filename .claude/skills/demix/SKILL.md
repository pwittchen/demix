---
name: demix
description: Translate natural-language audio-processing requests into a `demix` CLI invocation. Use whenever the user describes what they want to do with a song (download it from YouTube, cut a segment, slow it down, change its key, separate vocals/stems, etc.) rather than giving explicit flags. Works on local files, YouTube URLs, and text search queries.
---

# demix skill

You are driving the `demix` CLI that lives in this repository. The user will describe what they want in plain language. Your job is to pick the correct flags, print the final command, run it, and report the result.

## Workflow

1. **Parse intent.** Read the user's request and extract: source (URL / search / local file), time window, tempo change, pitch/key change, stem-separation mode, extras (video, key detection, cleanup).
2. **Map to flags.** Use the table below. Never invent flags that aren't there.
3. **Ask only if blocking.** If the source is ambiguous (e.g., user says "that song" with no context), ask one concise question. Otherwise proceed — prefer sensible defaults over interrogation.
4. **Show the command, then run it.** Print the exact `demix …` invocation you're about to execute, then run it via Bash. Do not paraphrase the user's request back to them.
5. **Report the result.** On success, point at `output/` (or the `-o` dir). On failure, surface stderr verbatim — don't guess fixes unless the cause is obvious.

## Source selection (mutually exclusive, exactly one required)

| User says… | Flag |
|---|---|
| a YouTube URL (starts with `http`, contains `youtube.com` or `youtu.be`) | `-u '<url>'` (quote it) |
| "search for…", "find…", `Artist - Song`, or just a song title without a URL or file | `-s '<query>'` |
| a path to a local file (ends in `.mp3`/`.wav`/`.flac`/`.m4a`/… or starts with `/`, `./`, `~`) | `-f '<path>'` |

If the user gives a URL that contains backslashes (terminal paste artifact), keep them — `demix` strips them itself.

## Time cutting

- "from 1:30", "starting at 1:30" → `-ss 1:30`
- "until 3:45", "first 2 minutes" (= `-to 2:00`), "up to 3:45" → `-to 3:45`
- "between 1:30 and 3:45", "clip 1:30–3:45" → `-ss 1:30 -to 3:45`
- Accepted formats: `MM:SS` or `HH:MM:SS`. Convert "90 seconds" → `1:30`, "1 hour" → `1:00:00`.

## Tempo (`-t`, float; 1.0 = unchanged)

- "slow down by 20%", "80% speed", "slower" (default: 0.8) → `-t 0.8`
- "half speed" → `-t 0.5`
- "speed up 25%", "1.25x" → `-t 1.25`
- "double speed" → `-t 2.0`
- Filter chains inside demix handle values outside 0.5–2.0, so large factors are fine.

## Pitch / key

Two mutually exclusive ways to change pitch — never combine `-p` and `-K`:

- **Semitones (explicit):** "down 5 semitones", "up a whole step" (= +2) → `-p -5` / `-p 2`. Range −12..+12.
- **Target key (automatic):** "transpose to A minor", "put it in C", "change key to F#" → `-K 'Am'` / `-K 'C'` / `-K 'F#'`. demix detects the current key and computes the shift.
- **Just detect the key, don't change it:** "what key is this in?", "detect the key" → `-k` (lowercase).

Key string accepts: `C`, `C#`, `Db`, `D`, …, `B`, optionally followed by `m`, `min`, `minor`, `maj`, `major` (default is major). Quote keys with `#` in the shell.

## Stem separation (`-m`, default `nosplit`)

| User wants… | Mode |
|---|---|
| "just download", "no separation", "just slow it down / change key" | `nosplit` (default — omit the flag) |
| "remove vocals", "instrumental", "karaoke", "acapella" | `2stems` (→ `vocals.mp3`, `accompaniment.mp3`) |
| "drums / bass / vocals / other" | `4stems` |
| "drums / bass / vocals / piano / other" | `5stems` |

First `2stems`/`4stems`/`5stems` run on a machine downloads ~300 MB of Spleeter models — warn the user once if the `pretrained_models/` directory doesn't exist yet.

## Extras

- **Karaoke video / accompaniment video** ("make a karaoke video", "video with the instrumental") → add `--video`. Only produces a video when `-m 2stems` is also set (demix silently skips it otherwise — mention this if the user asked for video with a different mode).
- **Custom output dir** ("save to ~/songs/x") → `-o '<dir>'`. Default is `./output`.
- **Cleanup** ("clean output", "delete models", "wipe everything") → `-c output` / `-c models` / `-c all`. Runs standalone; do not combine with a source flag.

## Defaults and decisions

- When the request is silent on something, don't add the flag. Defaults: `-t 1.0`, `-p 0`, `-m nosplit`, no cutting, no video, `-o output`.
- If the user says "karaoke" or "instrumental" without specifying a mode, assume `-m 2stems`.
- If the user asks for stems AND a tempo/pitch change, a single demix run handles both — don't chain invocations.
- Prefer `-K` over `-p` when the user names a target key; prefer `-p` when they name a semitone count.
- If the user gives a search query that's clearly an artist + song, use it verbatim — don't "correct" spelling.

## Running the command

`demix` and its dependencies (spleeter, essentia, pytubefix, ffmpeg bindings) live in a Python 3.8 virtualenv named `demix`. The tool will not work outside it. The Bash tool does not preserve shell state between calls, so **every invocation must activate the virtualenv inline**.

Resolve the binary in this order, picking the first that works:

1. **Already inside the right venv** — if `$VIRTUAL_ENV` ends in `/demix`, just run `demix …` directly.
2. **virtualenvwrapper layout** — if `~/.virtualenvs/demix/bin/activate` exists, prefix with `source ~/.virtualenvs/demix/bin/activate && demix …`.
3. **In-repo venv** — if `./venv/bin/activate` or `./.venv/bin/activate` exists in the repo root, source that one instead.
4. **Last resort** — fall back to `python demix.py …` from the repo root, but only if a venv is already active; if none is active, stop and tell the user the `demix` virtualenv isn't set up (point them at the README's `mkvirtualenv` step).

Quick probe before the first run in a session (one Bash call):

```
[ -n "$VIRTUAL_ENV" ] && echo "active: $VIRTUAL_ENV"; ls ~/.virtualenvs/demix/bin/activate 2>/dev/null; ls ./venv/bin/activate ./.venv/bin/activate 2>/dev/null
```

Then print the full command you're about to execute (including the `source … &&` prefix when used) and run it via Bash from the repo root. Typical shape:

```
source ~/.virtualenvs/demix/bin/activate && demix -s 'Queen - Bohemian Rhapsody' -m 2stems -t 0.9 -K 'Am' --video
```

If activation succeeds but `demix` exits with `ModuleNotFoundError` or `command not found`, the venv exists but isn't provisioned — surface the error and suggest `pip install -r requirements.txt` rather than retrying.

## Examples (natural language → command)

Examples below show the bare flag combination. In practice, prefix with the venv activation chosen by the resolution rules above (e.g., `source ~/.virtualenvs/demix/bin/activate && …`).

- "Download this and give me the instrumental: https://youtu.be/abc123"
  → `demix -u 'https://youtu.be/abc123' -m 2stems`
- "Find 'Radiohead Creep', slow it 15%, cut the first two minutes"
  → `demix -s 'Radiohead Creep' -t 0.85 -to 2:00`
- "~/Music/song.mp3 — transpose to G minor and split into 4 stems"
  → `demix -f '~/Music/song.mp3' -m 4stems -K 'Gm'`
- "What key is song.wav in?"
  → `demix -f 'song.wav' -k`
- "Make a karaoke video from 'Adele - Hello'"
  → `demix -s 'Adele - Hello' -m 2stems --video`
- "Clean up the output folder"
  → `demix -c output`

## What NOT to do

- Don't invent flags (`--loud`, `--normalize`, `--format mp3` — none exist).
- Don't combine `-u`, `-s`, and `-f`.
- Don't combine `-p` and `-K`.
- Don't run a cleanup (`-c`) in the same invocation as a source.
- Don't claim a video was generated when `-m` wasn't `2stems`.
- Don't re-run on failure with guessed fixes — report the error and ask.
