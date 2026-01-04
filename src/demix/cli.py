"""Command-line interface for demix."""

import argparse
import subprocess
import os
import shutil
import sys
import threading
import itertools
import time
from pytubefix import YouTube, Search
import essentia.standard as es


def get_version():
    """Get version from package metadata or fallback."""
    try:
        from demix import __version__
        return __version__
    except ImportError:
        return "1.0.0"


DEFAULT_VIDEO_RESOLUTION = "1280x720"

STEM_MODES = {
    "2stems": ["vocals", "accompaniment"],
    "4stems": ["vocals", "drums", "bass", "other"],
    "5stems": ["vocals", "drums", "bass", "piano", "other"],
}

# Mapping of note names to semitone values (C = 0)
NOTE_TO_SEMITONE = {
    "C": 0, "C#": 1, "Db": 1,
    "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5,
    "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11, "B#": 0,
}

# Valid key names for CLI help text
VALID_KEYS = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"]


def parse_time(time_str):
    """Parse time string in MM:SS or HH:MM:SS format to seconds."""
    if time_str is None:
        return None
    parts = time_str.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    else:
        raise ValueError(f"Invalid time format: {time_str}. Use MM:SS or HH:MM:SS")


def format_time(seconds):
    """Format seconds to MM:SS or HH:MM:SS string."""
    if seconds is None:
        return None
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
    return f"{minutes}:{secs:05.2f}"


def _strip_scale_suffix(key_str):
    """Strip scale suffix from key string and return (stripped_key, scale)."""
    lower = key_str.lower()
    suffixes = [
        (" minor", "minor", 6), (" major", "major", 6),
        ("min", "minor", 3), ("maj", "major", 3),
    ]
    for suffix, scale, length in suffixes:
        if lower.endswith(suffix):
            return key_str[:-length].strip(), scale
    # Handle 'm' suffix: 'Am', 'Cm', 'C#m', 'Bbm'
    if len(key_str) >= 2 and key_str[-1].lower() == "m":
        # Check it's not part of accidental (second-to-last char isn't # or b)
        if len(key_str) == 2 or (key_str[-2] != "#" and key_str[-2].lower() != "b"):
            return key_str[:-1], "minor"
        elif len(key_str) >= 3:
            return key_str[:-1], "minor"
    return key_str, "major"


def _extract_note(key_str):
    """Extract note name from key string. Returns note or None."""
    if len(key_str) == 0:
        return None
    note = key_str[0].upper()
    if len(key_str) > 1:
        modifier = key_str[1]
        if modifier == "#":
            note += "#"
        elif modifier.lower() == "b":
            note += "b"
    return note


def parse_key(key_str):
    """Parse a key string like 'C', 'Am', 'F# minor', 'Bbm' into (note, scale).

    Returns tuple of (note, scale) where scale is 'major' or 'minor'.
    Returns (None, None) if parsing fails.
    """
    if not key_str:
        return None, None

    original = key_str.strip()
    key_str, scale = _strip_scale_suffix(original)
    note = _extract_note(key_str)

    if note is None or note not in NOTE_TO_SEMITONE:
        raise ValueError(f"Invalid key: '{original}'. Valid keys: {', '.join(VALID_KEYS)}")

    return note, scale


def calculate_transpose_semitones(from_key, from_scale, to_key, to_scale):
    """Calculate the number of semitones to transpose from one key to another.

    Returns the shortest transposition (between -6 and +6 semitones).
    Returns 0 if the keys are the same.
    """
    from_semitone = NOTE_TO_SEMITONE[from_key]
    to_semitone = NOTE_TO_SEMITONE[to_key]

    # Calculate the difference
    diff = to_semitone - from_semitone

    # Normalize to shortest path (-6 to +6)
    if diff > 6:
        diff -= 12
    elif diff < -6:
        diff += 12

    return diff


class Spinner:
    def __init__(self, message="Loading..."):
        self.message = message
        self.spinning = False
        self.thread = None
        self.spinner_chars = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])

    def _spin(self):
        while self.spinning:
            char = next(self.spinner_chars)
            sys.stdout.write(f"\r{char} {self.message}")
            sys.stdout.flush()
            time.sleep(0.1)

    def start(self):
        self.spinning = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()

    def stop(self, success=True):
        self.spinning = False
        if self.thread:
            self.thread.join()
        symbol = "\033[32m✓\033[0m" if success else "\033[31m✗\033[0m"
        sys.stdout.write(f"\r{symbol} {self.message}\n")
        sys.stdout.flush()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop(success=exc_type is None)


def check_ffmpeg():
    """Check if ffmpeg and ffprobe are installed and accessible."""
    if shutil.which("ffmpeg") is None:
        print("Error: ffmpeg is not installed or not found in PATH.")
        print("Please install ffmpeg:")
        print("  macOS:   brew install ffmpeg")
        print("  Ubuntu:  sudo apt install ffmpeg")
        print("  Windows: https://ffmpeg.org/download.html")
        return False
    if shutil.which("ffprobe") is None:
        print("Error: ffprobe is not installed or not found in PATH.")
        print("ffprobe is usually included with ffmpeg. Please reinstall ffmpeg.")
        return False
    return True


def clean_url(url):
    """Remove backslashes from URL that may be added during terminal pasting."""
    if url:
        return url.replace("\\", "")
    return url


def search_youtube(query):
    """Search YouTube and return the URL of the first video result."""
    results = Search(query)
    videos = list(results.videos)
    if not videos:
        return None, None
    video = videos[0]
    return video.watch_url, video.title


def download_video(url, output_path):
    os.makedirs(output_path, exist_ok=True)
    yt = YouTube(url)
    stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
    ext = stream.mime_type.split("/")[-1]
    filename = f"video.{ext}"
    stream.download(output_path=output_path, filename=filename)
    return os.path.join(output_path, filename)


def convert_to_wav(input_file, output_file, start_time=None, end_time=None):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    cmd = ["ffmpeg"]
    if start_time is not None:
        cmd.extend(["-ss", str(start_time)])
    if end_time is not None:
        cmd.extend(["-to", str(end_time)])
    cmd.extend(["-i", input_file, "-vn", "-ar", "44100", "-ac", "2", output_file])
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def convert_wav_to_mp3(input_file, output_file, tempo=1.0, transpose=0):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    cmd = ["ffmpeg", "-i", input_file]
    filters = []
    # Apply transpose (pitch shift) using rubberband filter
    # Formula: pitch_ratio = 2^(semitones/12)
    if transpose != 0:
        pitch_ratio = 2 ** (transpose / 12)
        filters.append(f"rubberband=pitch={pitch_ratio}")
    # Apply tempo adjustment using atempo filter
    if tempo != 1.0:
        # atempo filter only accepts values between 0.5 and 2.0
        # chain multiple filters for values outside this range
        tempo_value = tempo
        while tempo_value < 0.5:
            filters.append("atempo=0.5")
            tempo_value /= 0.5
        while tempo_value > 2.0:
            filters.append("atempo=2.0")
            tempo_value /= 2.0
        filters.append(f"atempo={tempo_value}")
    if filters:
        cmd.extend(["-af", ",".join(filters)])
    cmd.extend(["-b:a", "192k", output_file])
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def separate_audio(mp3_file, output_folder, mode="2stems"):
    os.makedirs(output_folder, exist_ok=True)
    subprocess.run([
        "spleeter", "separate", "-p", f"spleeter:{mode}",
        "-o", output_folder, "-f", "{instrument}.{codec}", mp3_file
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def detect_key(audio_file):
    """Detect the musical key of an audio file using Essentia.

    Returns a tuple of (key, scale, strength) where:
    - key: The detected key (e.g., 'C', 'F#', 'Bb')
    - scale: 'major' or 'minor'
    - strength: Confidence score (0.0-1.0)
    """
    audio = es.MonoLoader(filename=audio_file)()
    key_extractor = es.KeyExtractor()
    key, scale, strength = key_extractor(audio)
    return key, scale, strength


def create_empty_mkv_with_audio(mp3_file, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    duration_cmd = [
        "ffprobe", "-i", mp3_file, "-show_entries", "format=duration",
        "-v", "quiet", "-of", "csv=p=0"
    ]
    duration = subprocess.check_output(duration_cmd).decode().strip()
    ffmpeg_cmd = [
        "ffmpeg", "-f", "lavfi", "-i", f"color=c=black:s={DEFAULT_VIDEO_RESOLUTION}:d={duration}",
        "-i", mp3_file, "-c:v", "libx264", "-c:a", "aac", "-strict", "experimental",
        "-shortest", output_file
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def remove_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"Removed: {path}")
    else:
        print(f"Directory does not exist: {path}")


def clean(target, output_dir="output"):
    if target == "output":
        remove_dir(output_dir)
    elif target == "models":
        remove_dir("pretrained_models")
    elif target == "all":
        remove_dir(output_dir)
        remove_dir("pretrained_models")


def parse_args():
    # Custom formatter with wider help position for better readability
    class WideHelpFormatter(argparse.RawDescriptionHelpFormatter):
        def __init__(self, prog):
            super().__init__(prog, max_help_position=40)

    parser = argparse.ArgumentParser(
        prog="demix",
        description="Separate audio into stems (vocals, instruments) from a YouTube video or local audio file.",
        epilog="Examples:\n"
               "  demix -u 'https://www.youtube.com/watch?v=VIDEO_ID' -m 4stems\n"
               "  demix -s 'Queen - Bohemian Rhapsody' -m 4stems\n"
               "  demix -f /path/to/song.mp3 -m 2stems\n"
               "  demix -f song.mp3 -ss 1:30 -to 3:45      # cut from 1:30 to 3:45\n"
               "  demix -f song.mp3 -ss 0:30               # start from 0:30\n"
               "  demix -f song.mp3 -to 2:00               # cut first 2 minutes",
        formatter_class=WideHelpFormatter
    )
    parser.add_argument(
        "-u", "--url",
        metavar="URL",
        help="YouTube video URL to process"
    )
    parser.add_argument(
        "-s", "--search",
        metavar="QUERY",
        help="search YouTube for a song (e.g., 'Artist - Song Name')"
    )
    parser.add_argument(
        "-f", "--file",
        metavar="FILE",
        help="local audio file to process (mp3, wav, flac, etc.)"
    )
    parser.add_argument(
        "-o", "--output",
        default="output",
        metavar="DIR",
        help="output directory (default: output)"
    )
    parser.add_argument(
        "-c", "--clean",
        choices=["output", "models", "all"],
        metavar="TARGET",
        help="clean up files: output, models, or all"
    )
    parser.add_argument(
        "-t", "--tempo",
        type=float,
        default=1.0,
        metavar="FACTOR",
        help="tempo factor for output audio (default: 1.0, use < 1.0 to slow down, e.g., 0.8 for 80%% tempo)"
    )
    parser.add_argument(
        "-p", "--transpose",
        type=int,
        default=0,
        metavar="SEMITONES",
        help="transpose pitch by semitones (default: 0, range: -12 to +12, e.g., -5 for 5 semitones down)"
    )
    parser.add_argument(
        "-k", "--key",
        action="store_true",
        help="detect and display the musical key of the audio"
    )
    parser.add_argument(
        "-K", "--target-key",
        metavar="KEY",
        help="transpose audio to target key (e.g., 'C', 'Am', 'F#', 'Bbm'). "
             "Automatically detects current key and calculates required transposition"
    )
    parser.add_argument(
        "-ss", "--start",
        metavar="TIME",
        help="start time for cutting (format: MM:SS or HH:MM:SS, e.g., 1:30 for 1 min 30 sec)"
    )
    parser.add_argument(
        "-to", "--end",
        metavar="TIME",
        help="end time for cutting (format: MM:SS or HH:MM:SS, e.g., 3:45 for 3 min 45 sec)"
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["2stems", "4stems", "5stems"],
        default="2stems",
        metavar="MODE",
        help="separation mode: 2stems (vocals/accompaniment), "
             "4stems (vocals/drums/bass/other), "
             "5stems (vocals/drums/bass/piano/other). "
             "Default: 2stems"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {get_version()}"
    )
    return parser.parse_args()


def _validate_args(args):
    """Validate command line arguments. Returns error message or None."""
    sources = sum([bool(args.url), bool(args.search), bool(args.file)])
    if sources == 0:
        return "Error: --url, --search, or --file is required when not using --clean"
    if sources > 1:
        return "Error: --url, --search, and --file cannot be used together"
    if args.file and not os.path.isfile(args.file):
        return f"Error: File not found: {args.file}"
    if args.target_key and args.transpose != 0:
        return "Error: --target-key and --transpose cannot be used together"
    if args.target_key:
        try:
            parse_key(args.target_key)
        except ValueError as e:
            return f"Error: {e}"
    return None


def _setup_directories(output_dir):
    """Create and return directory paths."""
    music_dir = os.path.join(output_dir, "music")
    return {
        "music": music_dir,
        "wav": os.path.join(music_dir, "wav"),
        "mp3": os.path.join(music_dir, "mp3"),
        "video": os.path.join(output_dir, "video"),
    }


def _resolve_search(search_query):
    """If search query provided, search YouTube and return the URL."""
    if not search_query:
        return None, True
    with Spinner(f"Searching YouTube for '{search_query}'..."):
        url, title = search_youtube(search_query)
    if not url:
        print(f"Error: No results found for '{search_query}'")
        return None, False
    print(f"Found: {title}")
    return url, True


def _print_info(source, output_dir, mode, stems, start_time, end_time, start_str, end_str):
    """Print processing information."""
    print(f"Processing: {source}")
    print(f"Output directory: {output_dir}")
    print(f"Separation mode: {mode} ({', '.join(stems)})")
    if start_time is not None or end_time is not None:
        cut_info = "Cutting: "
        if start_time is not None:
            cut_info += f"from {start_str}"
        if end_time is not None:
            cut_info += f" to {end_str}" if start_time else f"to {end_str}"
        print(cut_info)
    print()


def _convert_source(url, local_file, dirs, start_time, end_time):
    """Download (if URL) and convert source to WAV and MP3."""
    wav_file = os.path.join(dirs["wav"], "music.wav")
    mp3_file = os.path.join(dirs["mp3"], "music.mp3")
    cut_msg = " and cutting" if start_time is not None or end_time is not None else ""

    if url:
        with Spinner("Downloading video..."):
            video_file = download_video(url, dirs["video"])
        with Spinner(f"Converting to WAV{cut_msg}..."):
            os.makedirs(dirs["wav"], exist_ok=True)
            convert_to_wav(video_file, wav_file, start_time, end_time)
    else:
        with Spinner(f"Converting audio file to WAV{cut_msg}..."):
            os.makedirs(dirs["wav"], exist_ok=True)
            convert_to_wav(local_file, wav_file, start_time, end_time)

    with Spinner("Generating MP3 file..."):
        os.makedirs(dirs["mp3"], exist_ok=True)
        convert_wav_to_mp3(wav_file, mp3_file)

    return wav_file, mp3_file


def _convert_stems(tempo, transpose, dirs, stems):
    """Convert separated stems to MP3 with optional effects."""
    effects = []
    if tempo != 1.0:
        effects.append(f"tempo: {tempo}x")
    if transpose != 0:
        sign = "+" if transpose > 0 else ""
        effects.append(f"transpose: {sign}{transpose} semitones")

    convert_msg = "Converting separated tracks to MP3..."
    if effects:
        convert_msg = f"Converting separated tracks to MP3 ({', '.join(effects)})..."

    with Spinner(convert_msg):
        for stem in stems:
            convert_wav_to_mp3(
                os.path.join(dirs["wav"], f"{stem}.wav"),
                os.path.join(dirs["mp3"], f"{stem}.mp3"),
                tempo,
                transpose
            )
    return effects


def _build_source_description(searched_url, url, search_query, file):
    """Build source description string for display."""
    if searched_url:
        return f"{searched_url} (searched: '{search_query}')"
    if url:
        return url
    return file


def _apply_effects_to_original(wav_file, dirs, tempo, transpose, effects):
    """Apply tempo/transpose effects to original music file if needed."""
    if tempo == 1.0 and transpose == 0:
        return
    modified_mp3 = os.path.join(dirs["music"], "music_modified.mp3")
    with Spinner(f"Applying effects to original music file ({', '.join(effects)})..."):
        convert_wav_to_mp3(wav_file, modified_mp3, tempo, transpose)


def _create_accompaniment_video(dirs, mode):
    """Create video for accompaniment track in 2stems mode."""
    if mode != "2stems":
        return
    with Spinner("Creating video for accompaniment track..."):
        create_empty_mkv_with_audio(
            os.path.join(dirs["mp3"], "accompaniment.mp3"),
            os.path.join(dirs["video"], "accompaniment.mkv"),
        )


def _print_first_run_notice():
    """Print notice about model download on first run."""
    if not os.path.exists("pretrained_models"):
        print("\033[33mℹ\033[0m First run detected - Spleeter models will be downloaded (~300MB).")
        print("  This is a one-time operation (unless you delete models with --clean models).")
        print("  Subsequent operations will be faster.\n")


def _detect_key_after_transpose(dirs, transpose):
    """Detect and display key after transpose if pitch was changed."""
    if transpose == 0:
        return
    modified_mp3 = os.path.join(dirs["music"], "music_modified.mp3")
    if os.path.exists(modified_mp3):
        _detect_and_display_key(modified_mp3, label="after transpose")


def _detect_and_display_key(audio_file, label=None):
    """Detect and display the musical key of the audio file."""
    spinner_msg = "Detecting musical key..."
    if label:
        spinner_msg = f"Detecting musical key ({label})..."
    with Spinner(spinner_msg):
        key, scale, strength = detect_key(audio_file)
    confidence_pct = int(strength * 100)
    label_suffix = f" ({label})" if label else ""
    print(f"\033[34m♪\033[0m Detected key{label_suffix}: {key} {scale} (confidence: {confidence_pct}%)\n")
    return key, scale, strength


def _calculate_target_key_transpose(audio_file, target_key_str):
    """Calculate transposition needed to reach target key.

    Returns tuple of (transpose_semitones, current_key_info, target_key_info, skip_transpose).
    If skip_transpose is True, the audio is already in the target key.
    """
    # Detect current key
    current_key, current_scale, strength = _detect_and_display_key(audio_file)

    # Parse target key
    target_key, target_scale = parse_key(target_key_str)

    # Calculate semitones needed
    semitones = calculate_transpose_semitones(current_key, current_scale, target_key, target_scale)

    current_info = f"{current_key} {current_scale}"
    target_info = f"{target_key} {target_scale}"

    # Check if already in target key (same root note)
    if semitones == 0:
        return 0, current_info, target_info, True

    return semitones, current_info, target_info, False


def _handle_target_key(wav_file, target_key_str):
    """Handle target key transposition. Returns transpose semitones or None on error."""
    try:
        parse_key(target_key_str)  # Validate early
        semitones, current_info, target_info, skip = _calculate_target_key_transpose(
            wav_file, target_key_str
        )
        if skip:
            print(f"\033[33m!\033[0m Audio is already in {target_info}. Skipping transposition.\n")
            return 0
        sign = "+" if semitones > 0 else ""
        print(f"\033[34m♪\033[0m Transposing from {current_info} to {target_info} "
              f"({sign}{semitones} semitones)\n")
        return semitones
    except ValueError as e:
        print(f"Error: {e}")
        return None


def _resolve_transpose(wav_file, args):
    """Determine transpose value from args. Returns (transpose, success)."""
    if args.target_key:
        result = _handle_target_key(wav_file, args.target_key)
        if result is None:
            return 0, False
        return result, True
    if args.key:
        _detect_and_display_key(wav_file)
    return args.transpose, True


def main():
    args = parse_args()

    if args.clean:
        clean(args.clean, args.output)
        return

    if not check_ffmpeg():
        return

    error = _validate_args(args)
    if error:
        print(error)
        print("Run with --help for usage information")
        return

    # Resolve search to URL if needed (immutable - doesn't modify args)
    searched_url, success = _resolve_search(args.search)
    if not success:
        return

    # Determine the URL to use (from search result or direct input)
    # Clean backslashes that may be added during terminal pasting
    url = searched_url if searched_url else clean_url(args.url)

    try:
        start_time = parse_time(args.start)
        end_time = parse_time(args.end)
    except ValueError as e:
        print(f"Error: {e}")
        return

    dirs = _setup_directories(args.output)
    stems = STEM_MODES[args.mode]
    source = _build_source_description(searched_url, url, args.search, args.file)

    _print_info(source, args.output, args.mode, stems, start_time, end_time, args.start, args.end)
    remove_dir(args.output)

    wav_file, _ = _convert_source(url, args.file, dirs, start_time, end_time)

    transpose, success = _resolve_transpose(wav_file, args)
    if not success:
        return

    _print_first_run_notice()

    with Spinner(f"Separating audio ({args.mode})..."):
        separate_audio(wav_file, dirs["wav"], args.mode)

    effects = _convert_stems(args.tempo, transpose, dirs, stems)
    _apply_effects_to_original(wav_file, dirs, args.tempo, transpose, effects)

    if args.key or args.target_key:
        _detect_key_after_transpose(dirs, transpose)

    _create_accompaniment_video(dirs, args.mode)

    print(f"\n\033[32m✓\033[0m Done! Check the '{args.output}/' directory for results.")
    print(f"  Separated stems: {', '.join(stems)}")


if __name__ == "__main__":
    main()
