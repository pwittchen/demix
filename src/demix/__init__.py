"""
demix - Separate audio into stems (vocals, instruments) using AI.

A CLI tool that separates audio from songs into individual stems using
Spleeter. Supports YouTube downloads or local audio files, with options
for tempo/pitch adjustments and audio cutting.
"""

__version__ = "1.3.0"
__author__ = "Piotr Wittchen"

from demix.cli import (
    main,
    STEM_MODES,
    DEFAULT_VIDEO_RESOLUTION,
    NOTE_TO_SEMITONE,
    VALID_KEYS,
    Spinner,
    parse_args,
    parse_time,
    format_time,
    parse_key,
    calculate_transpose_semitones,
    remove_dir,
    clean,
    convert_wav_to_mp3,
    convert_to_wav,
    separate_audio,
    detect_key,
    download_video,
    create_empty_mkv_with_audio,
    check_ffmpeg,
    search_youtube,
    _resolve_search,
)

__all__ = [
    "__version__",
    "main",
    "STEM_MODES",
    "DEFAULT_VIDEO_RESOLUTION",
    "NOTE_TO_SEMITONE",
    "VALID_KEYS",
    "Spinner",
    "parse_args",
    "parse_time",
    "format_time",
    "parse_key",
    "calculate_transpose_semitones",
    "remove_dir",
    "clean",
    "convert_wav_to_mp3",
    "convert_to_wav",
    "separate_audio",
    "detect_key",
    "download_video",
    "create_empty_mkv_with_audio",
    "check_ffmpeg",
    "search_youtube",
    "_resolve_search",
]
