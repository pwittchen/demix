# demix

 [![version](https://img.shields.io/pypi/v/demix.svg)](https://pypi.python.org/pypi/demix/)
 [![build](https://github.com/pwittchen/demix/actions/workflows/build.yml/badge.svg)](https://github.com/pwittchen/demix/actions/workflows/build.yml)
 [![deploy](https://github.com/pwittchen/demix/actions/workflows/deploy.yml/badge.svg)](https://github.com/pwittchen/demix/actions/workflows/deploy.yml)
 [![release](https://github.com/pwittchen/demix/actions/workflows/release.yml/badge.svg)](https://github.com/pwittchen/demix/actions/workflows/release.yml)

separates audio from songs into stems (vocals, instruments), transposes music, changes tempo, detects music key, operates on music from youtube video or local file

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
| `-m`, `--mode` | Separation mode: `2stems`, `4stems`, or `5stems` (default: `2stems`) |
| `-c`, `--clean` | Clean up files: `output`, `models`, or `all` |
| `-v`, `--version` | Show version number |
| `-h`, `--help` | Show help message |

### separation modes

| Mode | Stems |
|------|-------|
| `2stems` | vocals, accompaniment |
| `4stems` | vocals, drums, bass, other |
| `5stems` | vocals, drums, bass, piano, other |

### examples

```bash
# separate a YouTube video into vocals and accompaniment
demix -u 'https://www.youtube.com/watch?v=VIDEO_ID'

# search YouTube by artist and song name
demix -s 'Queen - Bohemian Rhapsody' -m 4stems

# separate a local file with 4 stems
demix -f /path/to/song.mp3 -m 4stems

# cut audio from 1:30 to 3:45 before separation
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
```
