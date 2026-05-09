# demix

 [![version](https://img.shields.io/pypi/v/demix.svg)](https://pypi.python.org/pypi/demix/)
 [![build](https://github.com/pwittchen/demix/actions/workflows/build.yml/badge.svg)](https://github.com/pwittchen/demix/actions/workflows/build.yml)
 [![release](https://github.com/pwittchen/demix/actions/workflows/release.yml/badge.svg)](https://github.com/pwittchen/demix/actions/workflows/release.yml)

audio processing tool: download from YouTube or use local files, separate stems, adjust tempo/pitch, detect and transpose key, and cut segments.

## prerequisites

> [!NOTE]
> Please note: I'm using homebrew for installing `virtualenvwrapper` and `ffmpeg`.
If you're using another package manager or different operating system than macOS (e.g. Linux), you need to install it differently. In the examples for creating virtualenv below, replace python path below with your own python3.8 path. I'm personally using pyenv for installing various python verions, but you can do it as you wish.

## installation

I suggest to create virtualenv for this project to not break existing system-wide installations:

```
brew install virtualenvwrapper
brew install ffmpeg
mkdir demix
cd demix
mkvirtualenv -p /Users/pw/.pyenv/versions/3.8.16/bin/python demix
workon demix
pip install demix
demix -v
```

## update

```
pip install demix --upgrade
```

## development

prepare environment:

```
brew install virtualenvwrapper
brew install ffmpeg
git clone git@github.com:pwittchen/demix.git
cd demix
mkvirtualenv -p /Users/pw/.pyenv/versions/3.8.16/bin/python demix
workon demix
pip install -r requirements.txt
python demix.py -v
```

## virtualenv

exit virtualenv, when you're done:

```
deactivate
```

to activate env again:

```
workon demix
```

## testing

install `pytest`:

```
pip install pytest
```

run all tests (`-v` param for verbose):

```
pytest -v
```

## versioning and deployment

When we create and push a new git tag, e.g. `v1.0.4`, `deploy.yml` github action is triggered. It automatically extracts created tag, updates version with `bump_version.py` script, performs git commit and push. After that, deployment of the new package version to PyPi is executed.

## usage

```
demix -u <youtube-url> [options]
demix -s <search-query> [options]
demix -f <audio-file> [options]
```

### options

| Option | Description |
|--------|-------------|
| `-u`, `--url` | YouTube video URL to process |
| `-s`, `--search` | Search YouTube for a song (e.g., `'Artist - Song Name'`) |
| `-f`, `--file` | Local audio file to process (mp3, wav, flac, etc.) |
| `-o`, `--output` | Output directory (default: `output`) |
| `-t`, `--tempo` | Tempo factor for output audio (default: `1.0`, use `< 1.0` to slow down) |
| `-p`, `--transpose` | Transpose pitch by semitones (default: `0`, range: `-12` to `+12`) |
| `-k`, `--key` | Detect and display the musical key of the audio |
| `-K`, `--target-key` | Transpose audio to target key (e.g., `C`, `Am`, `F#`, `Bb minor`) |
| `-ss`, `--start` | Start time for cutting (format: `MM:SS` or `HH:MM:SS`) |
| `-to`, `--end` | End time for cutting (format: `MM:SS` or `HH:MM:SS`) |
| `-m`, `--mode` | Processing mode: `nosplit`, `2stems`, `4stems`, or `5stems` (default: `nosplit`) |
| `--video` | Generate video: accompaniment track in `2stems` mode, or the output music track in `nosplit` mode (default: skip video generation) |
| `-q`, `--quiet` | Suppress progress messages and spinners; print only the final result and errors |
| `-c`, `--clean` | Clean up files: `output`, `models`, or `all` |
| `-v`, `--version` | Show version number |
| `-h`, `--help` | Show help message |

### modes

| Mode | Description |
|------|-------------|
| `nosplit` | No stem separation (download, convert, and apply effects only) |
| `2stems` | vocals, accompaniment |
| `4stems` | vocals, drums, bass, other |
| `5stems` | vocals, drums, bass, piano, other |

### examples

```bash
# separate a YouTube video into vocals and accompaniment
demix -u 'https://www.youtube.com/watch?v=VIDEO_ID' -m 2stems

# search YouTube by artist and song name
demix -s 'Queen - Bohemian Rhapsody' -m 4stems

# separate a local file with 4 stems
demix -f /path/to/song.mp3 -m 4stems

# cut audio from 1:30 to 3:45
demix -f song.mp3 -ss 1:30 -to 3:45

# start from 0:30 (skip intro)
demix -f song.mp3 -ss 0:30

# keep only the first 2 minutes
demix -f song.mp3 -to 2:00

# combine cutting with tempo and transpose
demix -f song.mp3 -ss 1:00 -to 4:00 -t 0.8 -p -2

# detect musical key of a song
demix -f song.mp3 -k

# detect key before and after transposing
demix -f song.mp3 -k -p -3

# transpose to a specific key (auto-detects current key)
demix -f song.mp3 -K C

# transpose to A minor
demix -f song.mp3 -K Am

# transpose to target key with tempo change
demix -f song.mp3 -K "F# minor" -t 0.9

# slow down without separating stems
demix -f song.mp3 -t 0.8 -m nosplit

# download and cut without separation
demix -u 'https://www.youtube.com/watch?v=VIDEO_ID' -ss 1:00 -to 3:00 -m nosplit

# run silently and only print the final result message
demix -f song.mp3 -m 4stems -q
```

## MCP server

The repo also ships an [MCP](https://modelcontextprotocol.io) server at [`mcp/`](mcp/) so LLM clients (Claude Desktop, Claude Code, etc.) can call demix directly. It's a sibling Python package (`demix-mcp`, Python 3.10+) that shells out to the `demix` CLI on PATH — keeping it decoupled from demix's own Python 3.8 environment.

Install (in a separate Python 3.10+ env):

```bash
pipx install ./mcp
```

### Claude Code

Register the server with the `claude mcp` CLI (run from your demix workspace so `pretrained_models/` and `output/` cache there):

```bash
claude mcp add-json demix '{"command":"demix-mcp","cwd":"'"$PWD"'"}'
```

Add `--scope user` to make it available across all projects, or `--scope project` to commit it into `.mcp.json` for your team. Verify with:

```bash
claude mcp list
```

Inside Claude Code, run `/mcp` to inspect server status and the exposed tools.

### Claude Desktop / other clients

Add the server to `~/Library/Application Support/Claude/claude_desktop_config.json` (or your client's equivalent):

```json
{
  "mcpServers": {
    "demix": {
      "command": "demix-mcp",
      "cwd": "/path/to/demix-workspace"
    }
  }
}
```

Tools exposed: `process_audio`, `detect_key`, `search_youtube`, `clean`. See [`mcp/README.md`](mcp/README.md) for details.

## Claude Code skill

This repo ships a [Claude Code](https://claude.com/claude-code) skill at [`.claude/skills/demix/SKILL.md`](.claude/skills/demix/SKILL.md) that translates plain-English requests into `demix` invocations — describe what you want and Claude picks the flags, shows the command, and runs it.

Examples of requests the skill handles:

- *"Download `https://youtu.be/abc123` and give me the instrumental"* → `demix -u 'https://youtu.be/abc123' -m 2stems`
- *"Find 'Radiohead Creep', slow it 15%, keep only the first two minutes"* → `demix -s 'Radiohead Creep' -t 0.85 -to 2:00`
- *"`~/Music/song.mp3` — transpose to G minor and split into 4 stems"* → `demix -f '~/Music/song.mp3' -m 4stems -K 'Gm'`
- *"What key is `song.wav` in?"* → `demix -f 'song.wav' -k`
- *"Make a karaoke video from 'Adele - Hello'"* → `demix -s 'Adele - Hello' -m 2stems --video`

Trigger it by typing `/demix` in Claude Code, or just describe the task in natural language — the skill loads automatically when the intent matches.
