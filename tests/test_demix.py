import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
import pytest

# Add src directory to path for development usage
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from demix import (  # noqa: E402
    __version__,
    DEFAULT_VIDEO_RESOLUTION,
    STEM_MODES,
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
    main,
)


class TestVersion:
    def test_version_is_string(self):
        assert isinstance(__version__, str)

    def test_version_format(self):
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestStemModes:
    def test_2stems_mode(self):
        assert "2stems" in STEM_MODES
        assert STEM_MODES["2stems"] == ["vocals", "accompaniment"]

    def test_4stems_mode(self):
        assert "4stems" in STEM_MODES
        assert STEM_MODES["4stems"] == ["vocals", "drums", "bass", "other"]

    def test_5stems_mode(self):
        assert "5stems" in STEM_MODES
        assert STEM_MODES["5stems"] == ["vocals", "drums", "bass", "piano", "other"]

    def test_all_modes_have_vocals(self):
        for mode, stems in STEM_MODES.items():
            assert "vocals" in stems, f"Mode {mode} should have vocals"


class TestParseTime:
    def test_parse_time_none(self):
        assert parse_time(None) is None

    def test_parse_time_minutes_seconds(self):
        assert parse_time("1:30") == 90.0

    def test_parse_time_zero_minutes(self):
        assert parse_time("0:45") == 45.0

    def test_parse_time_with_decimal_seconds(self):
        assert parse_time("2:30.5") == 150.5

    def test_parse_time_hours_minutes_seconds(self):
        assert parse_time("1:30:00") == 5400.0

    def test_parse_time_full_format(self):
        assert parse_time("1:15:30") == 4530.0

    def test_parse_time_invalid_format(self):
        with pytest.raises(ValueError) as excinfo:
            parse_time("invalid")
        assert "Invalid time format" in str(excinfo.value)

    def test_parse_time_too_many_colons(self):
        with pytest.raises(ValueError) as excinfo:
            parse_time("1:2:3:4")
        assert "Invalid time format" in str(excinfo.value)


class TestFormatTime:
    def test_format_time_none(self):
        assert format_time(None) is None

    def test_format_time_seconds_only(self):
        result = format_time(45.0)
        assert result == "0:45.00"

    def test_format_time_minutes_seconds(self):
        result = format_time(90.0)
        assert result == "1:30.00"

    def test_format_time_with_hours(self):
        result = format_time(3661.5)
        assert result == "1:01:01.50"

    def test_format_time_zero(self):
        result = format_time(0)
        assert result == "0:00.00"


class TestParseArgs:
    def test_url_argument(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test"]):
            args = parse_args()
            assert args.url == "https://youtube.com/watch?v=test"

    def test_default_output(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test"]):
            args = parse_args()
            assert args.output == "output"

    def test_custom_output(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-o", "my_output"]):
            args = parse_args()
            assert args.output == "my_output"

    def test_default_tempo(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com"]):
            args = parse_args()
            assert args.tempo == 1.0

    def test_custom_tempo(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-t", "0.8"]):
            args = parse_args()
            assert args.tempo == 0.8

    def test_default_mode(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com"]):
            args = parse_args()
            assert args.mode == "2stems"

    def test_mode_4stems(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-m", "4stems"]):
            args = parse_args()
            assert args.mode == "4stems"

    def test_mode_5stems(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-m", "5stems"]):
            args = parse_args()
            assert args.mode == "5stems"

    def test_clean_argument(self):
        with patch.object(sys, "argv", ["demix", "-c", "output"]):
            args = parse_args()
            assert args.clean == "output"

    def test_clean_models(self):
        with patch.object(sys, "argv", ["demix", "-c", "models"]):
            args = parse_args()
            assert args.clean == "models"

    def test_clean_all(self):
        with patch.object(sys, "argv", ["demix", "-c", "all"]):
            args = parse_args()
            assert args.clean == "all"

    def test_file_argument(self):
        with patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3"]):
            args = parse_args()
            assert args.file == "/path/to/song.mp3"

    def test_file_argument_long_form(self):
        with patch.object(sys, "argv", ["demix", "--file", "/path/to/song.wav"]):
            args = parse_args()
            assert args.file == "/path/to/song.wav"

    def test_file_with_options(self):
        with patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-m", "4stems", "-t", "0.9"]):
            args = parse_args()
            assert args.file == "/path/to/song.mp3"
            assert args.mode == "4stems"
            assert args.tempo == 0.9

    def test_no_url_or_file_defaults_to_none(self):
        with patch.object(sys, "argv", ["demix", "-c", "output"]):
            args = parse_args()
            assert args.url is None
            assert args.file is None

    def test_search_argument_short_form(self):
        with patch.object(sys, "argv", ["demix", "-s", "Queen - Bohemian Rhapsody"]):
            args = parse_args()
            assert args.search == "Queen - Bohemian Rhapsody"

    def test_search_argument_long_form(self):
        with patch.object(sys, "argv", ["demix", "--search", "Artist - Song Name"]):
            args = parse_args()
            assert args.search == "Artist - Song Name"

    def test_search_with_options(self):
        with patch.object(sys, "argv", ["demix", "-s", "Test Query", "-m", "4stems", "-t", "0.9"]):
            args = parse_args()
            assert args.search == "Test Query"
            assert args.mode == "4stems"
            assert args.tempo == 0.9

    def test_search_defaults_to_none(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com"]):
            args = parse_args()
            assert args.search is None

    def test_default_transpose(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com"]):
            args = parse_args()
            assert args.transpose == 0

    def test_custom_transpose_positive(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-p", "5"]):
            args = parse_args()
            assert args.transpose == 5

    def test_custom_transpose_negative(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-p", "-7"]):
            args = parse_args()
            assert args.transpose == -7

    def test_transpose_long_form(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "--transpose", "12"]):
            args = parse_args()
            assert args.transpose == 12

    def test_file_with_tempo_and_transpose(self):
        with patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-t", "0.9", "-p", "-3"]):
            args = parse_args()
            assert args.file == "/path/to/song.mp3"
            assert args.tempo == 0.9
            assert args.transpose == -3

    def test_default_start_end(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com"]):
            args = parse_args()
            assert args.start is None
            assert args.end is None

    def test_start_time_short_form(self):
        with patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-ss", "1:30"]):
            args = parse_args()
            assert args.start == "1:30"

    def test_start_time_long_form(self):
        with patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "--start", "2:00"]):
            args = parse_args()
            assert args.start == "2:00"

    def test_end_time_short_form(self):
        with patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-to", "3:45"]):
            args = parse_args()
            assert args.end == "3:45"

    def test_end_time_long_form(self):
        with patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "--end", "4:00"]):
            args = parse_args()
            assert args.end == "4:00"

    def test_start_and_end_time(self):
        with patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-ss", "1:00", "-to", "3:00"]):
            args = parse_args()
            assert args.start == "1:00"
            assert args.end == "3:00"

    def test_file_with_all_options(self):
        test_argv = [
            "demix", "-f", "/path/to/song.mp3", "-t", "0.8", "-p", "2",
            "-ss", "0:30", "-to", "2:30", "-m", "4stems"
        ]
        with patch.object(sys, "argv", test_argv):
            args = parse_args()
            assert args.file == "/path/to/song.mp3"
            assert args.tempo == 0.8
            assert args.transpose == 2
            assert args.start == "0:30"
            assert args.end == "2:30"
            assert args.mode == "4stems"


class TestSpinner:
    def test_spinner_init(self):
        spinner = Spinner("Test message")
        assert spinner.message == "Test message"
        assert spinner.spinning is False
        assert spinner.thread is None

    def test_spinner_default_message(self):
        spinner = Spinner()
        assert spinner.message == "Loading..."

    def test_spinner_context_manager(self):
        with patch.object(Spinner, "start") as mock_start:
            with patch.object(Spinner, "stop") as mock_stop:
                with Spinner("Test"):
                    mock_start.assert_called_once()
                mock_stop.assert_called_once_with(success=True)

    def test_spinner_context_manager_on_exception(self):
        with patch.object(Spinner, "start"):
            with patch.object(Spinner, "stop") as mock_stop:
                try:
                    with Spinner("Test"):
                        raise ValueError("Test error")
                except ValueError:
                    pass
                mock_stop.assert_called_once_with(success=False)


class TestRemoveDir:
    def test_remove_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = os.path.join(tmpdir, "test_remove")
            os.makedirs(test_dir)
            assert os.path.exists(test_dir)
            remove_dir(test_dir)
            assert not os.path.exists(test_dir)

    def test_remove_nonexistent_directory(self, capsys):
        remove_dir("/nonexistent/path/that/does/not/exist")
        captured = capsys.readouterr()
        assert "does not exist" in captured.out


class TestClean:
    def test_clean_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)
            assert os.path.exists(output_dir)
            clean("output", output_dir)
            assert not os.path.exists(output_dir)

    def test_clean_models(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                models_dir = os.path.join(tmpdir, "pretrained_models")
                os.makedirs(models_dir)
                assert os.path.exists(models_dir)
                clean("models")
                assert not os.path.exists(models_dir)
            finally:
                os.chdir(original_cwd)

    def test_clean_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                output_dir = os.path.join(tmpdir, "output")
                models_dir = os.path.join(tmpdir, "pretrained_models")
                os.makedirs(output_dir)
                os.makedirs(models_dir)
                clean("all", output_dir)
                assert not os.path.exists(output_dir)
                assert not os.path.exists(models_dir)
            finally:
                os.chdir(original_cwd)


class TestConvertWavToMp3:
    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_without_tempo_change(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=1.0)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffmpeg" in args
        assert "-i" in args
        assert "-af" not in args

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_with_tempo_in_range(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=0.8)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_index = args.index("-af")
        assert "atempo=0.8" in args[af_index + 1]

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_with_tempo_below_half(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=0.25)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_index = args.index("-af")
        # Should chain multiple atempo filters for values < 0.5 tempo
        assert "atempo=0.5" in args[af_index + 1]

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_with_tempo_above_two(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=3.0)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_index = args.index("-af")
        # Should chain multiple atempo filters for values > 2.0 tempo
        assert "atempo=2.0" in args[af_index + 1]

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_without_transpose(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=1.0, transpose=0)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-af" not in args

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_with_transpose_positive(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=1.0, transpose=5)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_index = args.index("-af")
        # pitch_ratio = 2^(5/12) ≈ 1.3348
        assert "rubberband=pitch=" in args[af_index + 1]

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_with_transpose_negative(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=1.0, transpose=-7)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_index = args.index("-af")
        # pitch_ratio = 2^(-7/12) ≈ 0.6674
        assert "rubberband=pitch=" in args[af_index + 1]

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_with_transpose_octave_up(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=1.0, transpose=12)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_index = args.index("-af")
        # pitch_ratio = 2^(12/12) = 2.0 (one octave up)
        assert "rubberband=pitch=2.0" in args[af_index + 1]

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_with_transpose_octave_down(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=1.0, transpose=-12)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_index = args.index("-af")
        # pitch_ratio = 2^(-12/12) = 0.5 (one octave down)
        assert "rubberband=pitch=0.5" in args[af_index + 1]

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_with_tempo_and_transpose(self, mock_makedirs, mock_run):
        convert_wav_to_mp3("/input/file.wav", "/output/file.mp3", tempo=0.8, transpose=3)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "-af" in args
        af_index = args.index("-af")
        filter_chain = args[af_index + 1]
        # Should have both rubberband and atempo in the filter chain
        assert "rubberband=pitch=" in filter_chain
        assert "atempo=" in filter_chain
        # rubberband should come before atempo
        assert filter_chain.index("rubberband") < filter_chain.index("atempo")


class TestConvertToWav:
    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_to_wav_calls_ffmpeg(self, mock_makedirs, mock_run):
        convert_to_wav("/input/video.mp4", "/output/audio.wav")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "ffmpeg"
        assert "-i" in args
        assert "/input/video.mp4" in args
        assert "/output/audio.wav" in args
        assert "-ar" in args
        assert "44100" in args

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_to_wav_without_time_params(self, mock_makedirs, mock_run):
        convert_to_wav("/input/video.mp4", "/output/audio.wav")
        args = mock_run.call_args[0][0]
        assert "-ss" not in args
        assert "-to" not in args

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_to_wav_with_start_time(self, mock_makedirs, mock_run):
        convert_to_wav("/input/video.mp4", "/output/audio.wav", start_time=90)
        args = mock_run.call_args[0][0]
        assert "-ss" in args
        ss_index = args.index("-ss")
        assert args[ss_index + 1] == "90"
        assert "-to" not in args

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_to_wav_with_end_time(self, mock_makedirs, mock_run):
        convert_to_wav("/input/video.mp4", "/output/audio.wav", end_time=180)
        args = mock_run.call_args[0][0]
        assert "-to" in args
        to_index = args.index("-to")
        assert args[to_index + 1] == "180"
        assert "-ss" not in args

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_convert_to_wav_with_start_and_end_time(self, mock_makedirs, mock_run):
        convert_to_wav("/input/video.mp4", "/output/audio.wav", start_time=60, end_time=180)
        args = mock_run.call_args[0][0]
        assert "-ss" in args
        assert "-to" in args
        ss_index = args.index("-ss")
        to_index = args.index("-to")
        assert args[ss_index + 1] == "60"
        assert args[to_index + 1] == "180"
        # -ss and -to should come before -i for fast seeking
        i_index = args.index("-i")
        assert ss_index < i_index
        assert to_index < i_index


class TestSeparateAudio:
    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_separate_audio_default_mode(self, mock_makedirs, mock_run):
        separate_audio("/input/music.mp3", "/output")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "spleeter"
        assert "separate" in args
        assert "-p" in args
        assert "spleeter:2stems" in args

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_separate_audio_4stems(self, mock_makedirs, mock_run):
        separate_audio("/input/music.mp3", "/output", mode="4stems")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "spleeter:4stems" in args

    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.os.makedirs")
    def test_separate_audio_5stems(self, mock_makedirs, mock_run):
        separate_audio("/input/music.mp3", "/output", mode="5stems")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "spleeter:5stems" in args


class TestDownloadVideo:
    @patch("demix.cli.YouTube")
    @patch("demix.cli.os.makedirs")
    def test_download_video(self, mock_makedirs, mock_youtube):
        mock_stream = MagicMock()
        mock_stream.mime_type = "audio/mp4"
        mock_stream.download.return_value = None
        mock_yt = MagicMock()
        mock_yt.streams.filter.return_value.order_by.return_value.desc.return_value.first.return_value = mock_stream
        mock_youtube.return_value = mock_yt

        result = download_video("https://youtube.com/watch?v=test", "/output")

        mock_makedirs.assert_called_once_with("/output", exist_ok=True)
        mock_youtube.assert_called_once_with("https://youtube.com/watch?v=test")
        assert result == "/output/video.mp4"


class TestSearchYoutube:
    @patch("demix.cli.Search")
    def test_search_youtube_returns_first_result(self, mock_search):
        mock_video = MagicMock()
        mock_video.watch_url = "https://youtube.com/watch?v=abc123"
        mock_video.title = "Test Song - Test Artist"
        mock_search.return_value.videos = [mock_video]

        url, title = search_youtube("Test Artist - Test Song")

        mock_search.assert_called_once_with("Test Artist - Test Song")
        assert url == "https://youtube.com/watch?v=abc123"
        assert title == "Test Song - Test Artist"

    @patch("demix.cli.Search")
    def test_search_youtube_no_results(self, mock_search):
        mock_search.return_value.videos = []

        url, title = search_youtube("nonexistent song xyz")

        assert url is None
        assert title is None

    @patch("demix.cli.Search")
    def test_search_youtube_multiple_results_returns_first(self, mock_search):
        mock_video1 = MagicMock()
        mock_video1.watch_url = "https://youtube.com/watch?v=first"
        mock_video1.title = "First Result"
        mock_video2 = MagicMock()
        mock_video2.watch_url = "https://youtube.com/watch?v=second"
        mock_video2.title = "Second Result"
        mock_search.return_value.videos = [mock_video1, mock_video2]

        url, title = search_youtube("test query")

        assert url == "https://youtube.com/watch?v=first"
        assert title == "First Result"


class TestResolveSearch:
    @patch("demix.cli.search_youtube")
    def test_resolve_search_no_search_query(self, mock_search):
        url, success = _resolve_search(None)

        assert url is None
        assert success is True
        mock_search.assert_not_called()

    @patch("demix.cli.search_youtube")
    def test_resolve_search_success(self, mock_search, capsys):
        mock_search.return_value = ("https://youtube.com/watch?v=test", "Test Title")

        url, success = _resolve_search("Artist - Song")

        assert success is True
        assert url == "https://youtube.com/watch?v=test"
        captured = capsys.readouterr()
        assert "Found: Test Title" in captured.out

    @patch("demix.cli.search_youtube")
    def test_resolve_search_no_results(self, mock_search, capsys):
        mock_search.return_value = (None, None)

        url, success = _resolve_search("nonexistent song")

        assert success is False
        assert url is None
        captured = capsys.readouterr()
        assert "No results found" in captured.out


class TestCreateEmptyMkvWithAudio:
    @patch("demix.cli.subprocess.run")
    @patch("demix.cli.subprocess.check_output")
    @patch("demix.cli.os.makedirs")
    def test_create_empty_mkv(self, mock_makedirs, mock_check_output, mock_run):
        mock_check_output.return_value = b"120.5\n"
        create_empty_mkv_with_audio("/input/audio.mp3", "/output/video.mkv")

        # Check ffprobe was called to get duration
        mock_check_output.assert_called_once()

        # Check ffmpeg was called to create video
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffmpeg" in args
        assert DEFAULT_VIDEO_RESOLUTION in str(args)  # default resolution


class TestCheckFfmpeg:
    @patch("demix.cli.shutil.which")
    def test_check_ffmpeg_all_found(self, mock_which):
        mock_which.side_effect = lambda x: f"/usr/bin/{x}"
        result = check_ffmpeg()
        assert result is True
        assert mock_which.call_count == 2

    @patch("demix.cli.shutil.which")
    def test_check_ffmpeg_missing_ffmpeg(self, mock_which, capsys):
        mock_which.side_effect = lambda x: None if x == "ffmpeg" else f"/usr/bin/{x}"
        result = check_ffmpeg()
        assert result is False
        captured = capsys.readouterr()
        assert "ffmpeg is not installed" in captured.out

    @patch("demix.cli.shutil.which")
    def test_check_ffmpeg_missing_ffprobe(self, mock_which, capsys):
        mock_which.side_effect = lambda x: None if x == "ffprobe" else f"/usr/bin/{x}"
        result = check_ffmpeg()
        assert result is False
        captured = capsys.readouterr()
        assert "ffprobe is not installed" in captured.out


class TestSpinnerStartStop:
    def test_spinner_start_sets_spinning_true(self):
        spinner = Spinner("Test")
        try:
            spinner.start()
            assert spinner.spinning is True
            assert spinner.thread is not None
            assert spinner.thread.is_alive()
        finally:
            spinner.stop()

    def test_spinner_stop_sets_spinning_false(self, capsys):
        spinner = Spinner("Test")
        spinner.start()
        spinner.stop()
        assert spinner.spinning is False
        captured = capsys.readouterr()
        assert "Test" in captured.out

    def test_spinner_stop_success_symbol(self, capsys):
        spinner = Spinner("Test message")
        spinner.start()
        spinner.stop(success=True)
        captured = capsys.readouterr()
        assert "✓" in captured.out

    def test_spinner_stop_failure_symbol(self, capsys):
        spinner = Spinner("Test message")
        spinner.start()
        spinner.stop(success=False)
        captured = capsys.readouterr()
        assert "✗" in captured.out


class TestMain:
    @patch("demix.cli.clean")
    @patch.object(sys, "argv", ["demix", "-c", "output"])
    def test_main_clean_mode(self, mock_clean):
        main()
        mock_clean.assert_called_once_with("output", "output")

    @patch("demix.cli.clean")
    @patch.object(sys, "argv", ["demix", "-c", "models", "-o", "custom_output"])
    def test_main_clean_with_custom_output(self, mock_clean):
        main()
        mock_clean.assert_called_once_with("models", "custom_output")

    @patch("demix.cli.check_ffmpeg", return_value=False)
    @patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test"])
    def test_main_ffmpeg_not_found(self, mock_check):
        # Should return early without error
        main()
        mock_check.assert_called_once()

    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch.object(sys, "argv", ["demix"])
    def test_main_no_url_or_file(self, mock_check, capsys):
        main()
        captured = capsys.readouterr()
        assert "--url, --search, or --file is required" in captured.out

    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-f", "/path/to/file.mp3"])
    def test_main_both_url_and_file(self, mock_check, capsys):
        main()
        captured = capsys.readouterr()
        assert "--url, --search, and --file cannot be used together" in captured.out

    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch.object(sys, "argv", ["demix", "-s", "Test Query", "-u", "https://test.com"])
    def test_main_both_search_and_url(self, mock_check, capsys):
        main()
        captured = capsys.readouterr()
        assert "--url, --search, and --file cannot be used together" in captured.out

    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch.object(sys, "argv", ["demix", "-s", "Test Query", "-f", "/path/to/file.mp3"])
    def test_main_both_search_and_file(self, mock_check, capsys):
        main()
        captured = capsys.readouterr()
        assert "--url, --search, and --file cannot be used together" in captured.out

    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch.object(sys, "argv", ["demix", "-s", "Test", "-u", "https://test.com", "-f", "/path/file.mp3"])
    def test_main_all_three_sources(self, mock_check, capsys):
        main()
        captured = capsys.readouterr()
        assert "--url, --search, and --file cannot be used together" in captured.out

    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch.object(sys, "argv", ["demix", "-f", "/nonexistent/file.mp3"])
    def test_main_file_not_found(self, mock_check, capsys):
        main()
        captured = capsys.readouterr()
        assert "File not found" in captured.out

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)  # pretrained_models exists
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test"])
    def test_main_url_workflow_2stems(
        self, mock_makedirs, mock_exists, mock_check, mock_remove, mock_download,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv
    ):
        main()
        mock_download.assert_called_once()
        mock_convert_wav.assert_called_once()
        mock_separate.assert_called_once()
        # 2stems has 2 stems to convert + 1 for music.wav to music.mp3
        assert mock_wav_to_mp3.call_count == 3
        # 2stems mode should create video
        mock_mkv.assert_called_once()

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test", "-m", "4stems"])
    def test_main_url_workflow_4stems_no_video(
        self, mock_makedirs, mock_exists, mock_check, mock_remove, mock_download,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv
    ):
        main()
        mock_separate.assert_called_once()
        # 4stems has 4 stems to convert + 1 for music.wav to music.mp3
        assert mock_wav_to_mp3.call_count == 5
        # 4stems mode should NOT create video
        mock_mkv.assert_not_called()

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3"])
    def test_main_file_workflow(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv
    ):
        main()
        # File mode should not call download_video
        mock_convert_wav.assert_called_once()
        mock_separate.assert_called_once()

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=False)  # pretrained_models does NOT exist
    @patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test"])
    def test_main_first_run_message(
        self, mock_exists, mock_check, mock_remove, mock_download,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, capsys
    ):
        main()
        captured = capsys.readouterr()
        assert "First run detected" in captured.out

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test", "-t", "0.8", "-p", "3"])
    def test_main_with_tempo_and_transpose(
        self, mock_exists, mock_check, mock_remove, mock_download,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, capsys
    ):
        main()
        # Check that tempo and transpose were passed to convert_wav_to_mp3 for stem conversions
        # First call is for music.wav to music.mp3 (no effects), rest are for stems with effects
        call_args = mock_wav_to_mp3.call_args_list
        # Skip the first call (music.wav to music.mp3 without effects)
        for call in call_args[1:]:
            assert call[0][2] == 0.8  # tempo
            assert call[0][3] == 3    # transpose
        captured = capsys.readouterr()
        assert "tempo: 0.8x" in captured.out
        assert "transpose: +3 semitones" in captured.out

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test", "-ss", "1:30", "-to", "3:45"])
    def test_main_with_time_cutting(
        self, mock_exists, mock_check, mock_remove, mock_download,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, capsys
    ):
        main()
        # Check that start_time and end_time were passed to convert_to_wav
        call_args = mock_convert_wav.call_args[0]
        assert call_args[2] == 90.0   # start_time (1:30 = 90 seconds)
        assert call_args[3] == 225.0  # end_time (3:45 = 225 seconds)
        captured = capsys.readouterr()
        assert "Cutting: from 1:30 to 3:45" in captured.out

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-ss", "0:30"])
    def test_main_with_start_time_only(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, capsys
    ):
        main()
        call_args = mock_convert_wav.call_args[0]
        assert call_args[2] == 30.0   # start_time
        assert call_args[3] is None   # end_time
        captured = capsys.readouterr()
        assert "Cutting: from 0:30" in captured.out

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-to", "2:00"])
    def test_main_with_end_time_only(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, capsys
    ):
        main()
        call_args = mock_convert_wav.call_args[0]
        assert call_args[2] is None   # start_time
        assert call_args[3] == 120.0  # end_time (2:00 = 120 seconds)
        captured = capsys.readouterr()
        assert "Cutting: to 2:00" in captured.out

    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-ss", "invalid"])
    def test_main_invalid_time_format(self, mock_isfile, mock_check, capsys):
        main()
        captured = capsys.readouterr()
        assert "Invalid time format" in captured.out

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.search_youtube", return_value=("https://youtube.com/watch?v=found", "Found Song"))
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-s", "Artist - Song Name"])
    def test_main_search_workflow(
        self, mock_makedirs, mock_exists, mock_check, mock_search,
        mock_remove, mock_download, mock_convert_wav, mock_separate,
        mock_wav_to_mp3, mock_mkv, capsys
    ):
        main()
        # Verify search was called with query
        mock_search.assert_called_once_with("Artist - Song Name")
        # Verify download was called with the found URL
        mock_download.assert_called_once()
        download_url = mock_download.call_args[0][0]
        assert download_url == "https://youtube.com/watch?v=found"
        # Check output shows found title
        captured = capsys.readouterr()
        assert "Found: Found Song" in captured.out

    @patch("demix.cli.search_youtube", return_value=(None, None))
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch.object(sys, "argv", ["demix", "-s", "nonexistent song xyz"])
    def test_main_search_no_results(self, mock_check, mock_search, capsys):
        main()
        mock_search.assert_called_once_with("nonexistent song xyz")
        captured = capsys.readouterr()
        assert "No results found" in captured.out

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.search_youtube", return_value=("https://youtube.com/watch?v=test", "Test Song"))
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-s", "Test Query", "-m", "4stems"])
    def test_main_search_workflow_4stems(
        self, mock_makedirs, mock_exists, mock_check, mock_search,
        mock_remove, mock_download, mock_convert_wav, mock_separate,
        mock_wav_to_mp3, mock_mkv
    ):
        main()
        mock_search.assert_called_once_with("Test Query")
        mock_separate.assert_called_once()
        # 4stems has 4 stems to convert + 1 for music.wav to music.mp3
        assert mock_wav_to_mp3.call_count == 5
        # 4stems mode should NOT create video
        mock_mkv.assert_not_called()

    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.search_youtube", return_value=("https://youtube.com/watch?v=test", "Test Song"))
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-s", "Test", "-ss", "1:00", "-to", "2:30", "-t", "0.9"])
    def test_main_search_with_options(
        self, mock_makedirs, mock_exists, mock_check, mock_search,
        mock_remove, mock_download, mock_convert_wav, mock_separate,
        mock_wav_to_mp3, mock_mkv, capsys
    ):
        main()
        mock_search.assert_called_once_with("Test")
        # Check time cutting was passed
        call_args = mock_convert_wav.call_args[0]
        assert call_args[2] == 60.0   # start_time
        assert call_args[3] == 150.0  # end_time
        captured = capsys.readouterr()
        assert "Cutting: from 1:00 to 2:30" in captured.out


class TestParseArgsKey:
    def test_key_default_false(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com"]):
            args = parse_args()
            assert args.key is False

    def test_key_short_form(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-k"]):
            args = parse_args()
            assert args.key is True

    def test_key_long_form(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "--key"]):
            args = parse_args()
            assert args.key is True

    def test_key_with_other_options(self):
        with patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-k", "-m", "4stems"]):
            args = parse_args()
            assert args.key is True
            assert args.mode == "4stems"


class TestDetectKey:
    @patch("demix.cli.es.KeyExtractor")
    @patch("demix.cli.es.MonoLoader")
    def test_detect_key_returns_tuple(self, mock_mono_loader, mock_key_extractor):
        # Mock the audio loading
        mock_audio = MagicMock()
        mock_mono_loader.return_value = MagicMock(return_value=mock_audio)

        # Mock the key extractor
        mock_extractor_instance = MagicMock()
        mock_extractor_instance.return_value = ("C", "major", 0.85)
        mock_key_extractor.return_value = mock_extractor_instance

        key, scale, strength = detect_key("/path/to/audio.wav")

        assert key == "C"
        assert scale == "major"
        assert strength == 0.85

    @patch("demix.cli.es.KeyExtractor")
    @patch("demix.cli.es.MonoLoader")
    def test_detect_key_minor(self, mock_mono_loader, mock_key_extractor):
        mock_audio = MagicMock()
        mock_mono_loader.return_value = MagicMock(return_value=mock_audio)

        mock_extractor_instance = MagicMock()
        mock_extractor_instance.return_value = ("A", "minor", 0.72)
        mock_key_extractor.return_value = mock_extractor_instance

        key, scale, strength = detect_key("/path/to/audio.wav")

        assert key == "A"
        assert scale == "minor"
        assert strength == 0.72

    @patch("demix.cli.es.KeyExtractor")
    @patch("demix.cli.es.MonoLoader")
    def test_detect_key_sharp(self, mock_mono_loader, mock_key_extractor):
        mock_audio = MagicMock()
        mock_mono_loader.return_value = MagicMock(return_value=mock_audio)

        mock_extractor_instance = MagicMock()
        mock_extractor_instance.return_value = ("F#", "major", 0.91)
        mock_key_extractor.return_value = mock_extractor_instance

        key, scale, strength = detect_key("/path/to/audio.wav")

        assert key == "F#"
        assert scale == "major"
        assert strength == 0.91


class TestMainWithKeyDetection:
    @patch("demix.cli.detect_key", return_value=("G", "major", 0.88))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test", "-k"])
    def test_main_with_key_detection(
        self, mock_makedirs, mock_exists, mock_check, mock_remove, mock_download,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        main()
        mock_detect_key.assert_called_once()
        captured = capsys.readouterr()
        assert "Detected key: G major" in captured.out
        assert "confidence: 88%" in captured.out

    @patch("demix.cli.detect_key")
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.download_video", return_value="/output/video/video.mp4")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-u", "https://youtube.com/watch?v=test"])
    def test_main_without_key_flag_skips_detection(
        self, mock_makedirs, mock_exists, mock_check, mock_remove, mock_download,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key
    ):
        main()
        mock_detect_key.assert_not_called()

    @patch("demix.cli.detect_key", return_value=("Bb", "minor", 0.65))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-k"])
    def test_main_key_detection_with_file_input(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        main()
        mock_detect_key.assert_called_once()
        captured = capsys.readouterr()
        assert "Detected key: Bb minor" in captured.out
        assert "confidence: 65%" in captured.out

    @patch("demix.cli.detect_key", return_value=("C", "major", 0.75))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-k", "-p", "3"])
    def test_main_key_detection_after_transpose(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        """Key detection should run twice when -k and -p are both specified."""
        main()
        # Should be called twice: once for original, once after transpose
        assert mock_detect_key.call_count == 2
        captured = capsys.readouterr()
        assert "Detected key: C major" in captured.out
        assert "Detected key (after transpose): C major" in captured.out

    @patch("demix.cli.detect_key", return_value=("A", "minor", 0.80))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-k", "-p", "0"])
    def test_main_key_detection_no_transpose_when_zero(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        """Key detection should run only once when transpose is 0."""
        main()
        # Should be called only once since transpose is 0
        mock_detect_key.assert_called_once()
        captured = capsys.readouterr()
        assert "after transpose" not in captured.out


class TestNoteToSemitone:
    def test_note_mapping_complete(self):
        """All standard notes should be in the mapping."""
        expected = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"]
        for note in expected:
            assert note in NOTE_TO_SEMITONE

    def test_enharmonic_equivalents(self):
        """Enharmonic equivalents should map to same semitone."""
        assert NOTE_TO_SEMITONE["C#"] == NOTE_TO_SEMITONE["Db"]
        assert NOTE_TO_SEMITONE["D#"] == NOTE_TO_SEMITONE["Eb"]
        assert NOTE_TO_SEMITONE["F#"] == NOTE_TO_SEMITONE["Gb"]
        assert NOTE_TO_SEMITONE["G#"] == NOTE_TO_SEMITONE["Ab"]
        assert NOTE_TO_SEMITONE["A#"] == NOTE_TO_SEMITONE["Bb"]

    def test_semitone_values(self):
        """Check specific semitone values."""
        assert NOTE_TO_SEMITONE["C"] == 0
        assert NOTE_TO_SEMITONE["D"] == 2
        assert NOTE_TO_SEMITONE["E"] == 4
        assert NOTE_TO_SEMITONE["F"] == 5
        assert NOTE_TO_SEMITONE["G"] == 7
        assert NOTE_TO_SEMITONE["A"] == 9
        assert NOTE_TO_SEMITONE["B"] == 11


class TestValidKeys:
    def test_valid_keys_count(self):
        """Should have 17 valid key names (including enharmonics)."""
        assert len(VALID_KEYS) == 17


class TestParseKey:
    def test_parse_key_none(self):
        assert parse_key(None) == (None, None)

    def test_parse_key_empty(self):
        assert parse_key("") == (None, None)

    def test_parse_key_simple_major(self):
        note, scale = parse_key("C")
        assert note == "C"
        assert scale == "major"

    def test_parse_key_sharp_major(self):
        note, scale = parse_key("F#")
        assert note == "F#"
        assert scale == "major"

    def test_parse_key_flat_major(self):
        note, scale = parse_key("Bb")
        assert note == "Bb"
        assert scale == "major"

    def test_parse_key_simple_minor_suffix(self):
        note, scale = parse_key("Am")
        assert note == "A"
        assert scale == "minor"

    def test_parse_key_sharp_minor_suffix(self):
        note, scale = parse_key("C#m")
        assert note == "C#"
        assert scale == "minor"

    def test_parse_key_flat_minor_suffix(self):
        note, scale = parse_key("Bbm")
        assert note == "Bb"
        assert scale == "minor"

    def test_parse_key_major_word(self):
        note, scale = parse_key("G major")
        assert note == "G"
        assert scale == "major"

    def test_parse_key_minor_word(self):
        note, scale = parse_key("E minor")
        assert note == "E"
        assert scale == "minor"

    def test_parse_key_min_suffix(self):
        note, scale = parse_key("Dmin")
        assert note == "D"
        assert scale == "minor"

    def test_parse_key_maj_suffix(self):
        note, scale = parse_key("Amaj")
        assert note == "A"
        assert scale == "major"

    def test_parse_key_lowercase(self):
        note, scale = parse_key("c")
        assert note == "C"
        assert scale == "major"

    def test_parse_key_lowercase_minor(self):
        note, scale = parse_key("am")
        assert note == "A"
        assert scale == "minor"

    def test_parse_key_lowercase_sharp(self):
        note, scale = parse_key("f#")
        assert note == "F#"
        assert scale == "major"

    def test_parse_key_lowercase_flat(self):
        note, scale = parse_key("bb")
        assert note == "Bb"
        assert scale == "major"

    def test_parse_key_invalid_raises(self):
        with pytest.raises(ValueError) as excinfo:
            parse_key("X")
        assert "Invalid key" in str(excinfo.value)

    def test_parse_key_invalid_shows_valid_keys(self):
        with pytest.raises(ValueError) as excinfo:
            parse_key("H")
        assert "Valid keys:" in str(excinfo.value)


class TestCalculateTransposeSemitones:
    def test_same_key_returns_zero(self):
        result = calculate_transpose_semitones("C", "major", "C", "major")
        assert result == 0

    def test_same_key_different_scale_returns_zero(self):
        # Same root note, different scale - still 0 semitones
        result = calculate_transpose_semitones("A", "minor", "A", "major")
        assert result == 0

    def test_c_to_g_is_negative_5(self):
        result = calculate_transpose_semitones("C", "major", "G", "major")
        # C=0, G=7, so 7-0=7. Since 7 > 6, it normalizes to 7-12=-5
        assert result == -5

    def test_g_to_c_is_positive_5(self):
        result = calculate_transpose_semitones("G", "major", "C", "major")
        # G=7, C=0, so 0-7=-7, which is < -6, so -7+12=5
        assert result == 5

    def test_c_to_f_sharp(self):
        result = calculate_transpose_semitones("C", "major", "F#", "major")
        # C=0, F#=6, so 6-0=6
        assert result == 6

    def test_f_sharp_to_c(self):
        result = calculate_transpose_semitones("F#", "major", "C", "major")
        # F#=6, C=0, so 0-6=-6
        assert result == -6

    def test_a_to_c(self):
        result = calculate_transpose_semitones("A", "minor", "C", "major")
        # A=9, C=0, so 0-9=-9, which is < -6, so -9+12=3
        assert result == 3

    def test_c_to_a(self):
        result = calculate_transpose_semitones("C", "major", "A", "minor")
        # C=0, A=9, so 9-0=9, which is > 6, so 9-12=-3
        assert result == -3

    def test_enharmonic_equivalent(self):
        result1 = calculate_transpose_semitones("C", "major", "C#", "major")
        result2 = calculate_transpose_semitones("C", "major", "Db", "major")
        assert result1 == result2 == 1


class TestParseArgsTargetKey:
    def test_target_key_default_none(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com"]):
            args = parse_args()
            assert args.target_key is None

    def test_target_key_short_form(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-K", "Am"]):
            args = parse_args()
            assert args.target_key == "Am"

    def test_target_key_long_form(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "--target-key", "F#"]):
            args = parse_args()
            assert args.target_key == "F#"

    def test_target_key_with_space(self):
        with patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-K", "C minor"]):
            args = parse_args()
            assert args.target_key == "C minor"


class TestValidateArgsTargetKey:
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch.object(sys, "argv", ["demix", "-u", "https://test.com", "-K", "Am", "-p", "3"])
    def test_target_key_and_transpose_error(self, mock_check, capsys):
        main()
        captured = capsys.readouterr()
        assert "--target-key and --transpose cannot be used together" in captured.out


class TestMainWithTargetKey:
    @patch("demix.cli.detect_key", return_value=("C", "major", 0.85))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-K", "G"])
    def test_main_target_key_transpose_up(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        """Transposing from C major to G major should be -5 semitones."""
        main()
        mock_detect_key.assert_called()
        captured = capsys.readouterr()
        assert "Detected key: C major" in captured.out
        assert "Transposing from C major to G major" in captured.out
        assert "-5 semitones" in captured.out

    @patch("demix.cli.detect_key", return_value=("G", "major", 0.85))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-K", "C"])
    def test_main_target_key_transpose_down(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        """Transposing from G major to C major should be +5 semitones."""
        main()
        captured = capsys.readouterr()
        assert "Transposing from G major to C major" in captured.out
        assert "+5 semitones" in captured.out

    @patch("demix.cli.detect_key", return_value=("A", "minor", 0.85))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-K", "Am"])
    def test_main_target_key_already_in_key(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        """When music is already in target key, should skip transposition."""
        main()
        captured = capsys.readouterr()
        assert "Audio is already in A minor" in captured.out
        assert "Skipping transposition" in captured.out

    @patch("demix.cli.detect_key", return_value=("C", "major", 0.85))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-K", "Cm"])
    def test_main_target_key_same_root_different_scale(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        """C major to C minor - same root, should skip."""
        main()
        captured = capsys.readouterr()
        assert "Audio is already in C minor" in captured.out

    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-K", "X"])
    def test_main_target_key_invalid(self, mock_isfile, mock_check, capsys):
        """Invalid target key should show error."""
        main()
        captured = capsys.readouterr()
        assert "Invalid key" in captured.out

    @patch("demix.cli.detect_key", return_value=("E", "minor", 0.85))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-K", "Am"])
    def test_main_target_key_applies_transpose(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        """Verify transpose value is applied to stem conversion."""
        main()
        # E=4, A=9, so A-E = 5 semitones
        call_args = mock_wav_to_mp3.call_args_list
        # Stems should be converted with transpose=5
        for call in call_args[1:]:
            assert call[0][3] == 5  # transpose

    @patch("demix.cli.detect_key", return_value=("D", "major", 0.85))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-K", "C", "-t", "0.9"])
    def test_main_target_key_with_tempo(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        """Target key should work with tempo option."""
        main()
        captured = capsys.readouterr()
        assert "Transposing from D major to C major" in captured.out
        # D=2, C=0, so 0-2=-2
        call_args = mock_wav_to_mp3.call_args_list
        for call in call_args[1:]:
            assert call[0][2] == 0.9   # tempo
            assert call[0][3] == -2    # transpose

    @patch("demix.cli.detect_key", return_value=("F#", "major", 0.85))
    @patch("demix.cli.create_empty_mkv_with_audio")
    @patch("demix.cli.convert_wav_to_mp3")
    @patch("demix.cli.separate_audio")
    @patch("demix.cli.convert_to_wav")
    @patch("demix.cli.remove_dir")
    @patch("demix.cli.check_ffmpeg", return_value=True)
    @patch("demix.cli.os.path.exists", return_value=True)
    @patch("demix.cli.os.path.isfile", return_value=True)
    @patch("demix.cli.os.makedirs")
    @patch.object(sys, "argv", ["demix", "-f", "/path/to/song.mp3", "-K", "C"])
    def test_main_target_key_tritone(
        self, mock_makedirs, mock_isfile, mock_exists, mock_check, mock_remove,
        mock_convert_wav, mock_separate, mock_wav_to_mp3, mock_mkv, mock_detect_key, capsys
    ):
        """F# to C is a tritone (6 semitones)."""
        main()
        captured = capsys.readouterr()
        # F#=6, C=0, so 0-6=-6
        assert "-6 semitones" in captured.out
