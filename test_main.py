import json
import os
import tempfile
import pytest
from datetime import datetime
from main import (
    format_date,
    sanitize_creator_name,
    sanitize_title,
    generate_filename,
    load_content_resources,
    save_content_resources,
    download_transcript
)


class TestDateFormatting:
    """Tests for date formatting functionality."""

    def test_format_date_basic(self):
        """Test basic date conversion from MM-DD-YYYY to MMDDYYYY."""
        assert format_date("01-08-2026") == "01082026"

    def test_format_date_different_months(self):
        """Test date formatting with different months."""
        assert format_date("12-19-2025") == "12192025"
        assert format_date("06-14-2025") == "06142025"

    def test_format_date_single_digit_day(self):
        """Test date formatting with single digit days."""
        assert format_date("09-01-2025") == "09012025"

    def test_format_date_leap_year(self):
        """Test date formatting with leap year date."""
        assert format_date("02-29-2024") == "02292024"

    def test_format_date_invalid_format(self):
        """Test that invalid date format raises ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            format_date("2025-12-19")  # Wrong format (YYYY-MM-DD instead of MM-DD-YYYY)
        assert "Invalid date format" in str(exc_info.value)
        assert "expected MM-DD-YYYY" in str(exc_info.value)

    def test_format_date_invalid_date(self):
        """Test that invalid date raises ValueError."""
        with pytest.raises(ValueError):
            format_date("13-01-2025")  # Invalid month

    def test_format_date_non_existent_date(self):
        """Test that non-existent date raises ValueError."""
        with pytest.raises(ValueError):
            format_date("02-30-2025")  # February 30th doesn't exist


class TestCreatorNameSanitization:
    """Tests for content creator name sanitization."""

    def test_sanitize_creator_name_with_spaces(self):
        """Test replacing spaces with underscores."""
        assert sanitize_creator_name("Money or Life 美股频道") == "Money_or_Life_美股频道"

    def test_sanitize_creator_name_no_spaces(self):
        """Test name without spaces remains unchanged."""
        assert sanitize_creator_name("CreatorName") == "CreatorName"

    def test_sanitize_creator_name_multiple_spaces(self):
        """Test multiple consecutive spaces."""
        assert sanitize_creator_name("Content  Creator  Name") == "Content__Creator__Name"

    def test_sanitize_creator_name_chinese_characters(self):
        """Test Chinese characters with spaces."""
        assert sanitize_creator_name("海伦子Hellen") == "海伦子Hellen"

    def test_sanitize_creator_name_invalid_windows_characters(self):
        """Test removal of invalid Windows filename characters."""
        assert sanitize_creator_name("Creator:Name") == "CreatorName"
        assert sanitize_creator_name("Creator/Name") == "CreatorName"
        assert sanitize_creator_name("Creator\\Name") == "CreatorName"
        assert sanitize_creator_name("Creator|Name") == "CreatorName"
        assert sanitize_creator_name("Creator?Name") == "CreatorName"
        assert sanitize_creator_name("Creator*Name") == "CreatorName"
        assert sanitize_creator_name('Creator"Name') == "CreatorName"
        assert sanitize_creator_name("Creator<Name>") == "CreatorName"

    def test_sanitize_creator_name_leading_trailing_periods(self):
        """Test removal of leading/trailing periods and spaces."""
        assert sanitize_creator_name("...Creator Name...") == "Creator_Name"
        assert sanitize_creator_name("  Creator Name  ") == "Creator_Name"

    def test_sanitize_creator_name_control_characters(self):
        """Test removal of control characters."""
        assert sanitize_creator_name("Creator\x00Name") == "CreatorName"
        assert sanitize_creator_name("Creator\x1fName") == "CreatorName"

    def test_sanitize_creator_name_empty_result(self):
        """Test that empty result after sanitization returns 'Unknown'."""
        assert sanitize_creator_name(":::") == "Unknown"
        assert sanitize_creator_name("...") == "Unknown"

    def test_sanitize_creator_name_complex_mixed(self):
        """Test complex mixed case with special characters and Chinese."""
        assert sanitize_creator_name("Creator: 海伦子?") == "Creator_海伦子"


class TestTitleSanitization:
    """Tests for video title sanitization."""

    def test_sanitize_title_spaces_become_dashes(self):
        assert sanitize_title("My Cool Video") == "My-Cool-Video"

    def test_sanitize_title_removes_invalid_chars(self):
        assert sanitize_title('Title: "Subtitle"') == "Title-Subtitle"

    def test_sanitize_title_collapses_multiple_dashes(self):
        assert sanitize_title("A  B") == "A-B"

    def test_sanitize_title_strips_leading_trailing_dashes(self):
        assert sanitize_title("  Title  ") == "Title"

    def test_sanitize_title_max_length(self):
        long_title = "A" * 200
        result = sanitize_title(long_title, max_length=50)
        assert len(result) <= 50

    def test_sanitize_title_max_length_no_trailing_dash(self):
        title = "Word " * 20  # "Word Word Word ..." with spaces becoming dashes
        result = sanitize_title(title, max_length=10)
        assert not result.endswith("-")
        assert len(result) <= 10

    def test_sanitize_title_empty_after_sanitization(self):
        assert sanitize_title(':::') == "Untitled"

    def test_sanitize_title_chinese(self):
        assert sanitize_title("用最啰嗦的方式去火星") == "用最啰嗦的方式去火星"

    def test_sanitize_title_cjk_punctuation(self):
        """Full-width CJK punctuation becomes dashes, not left raw in the filename."""
        result = sanitize_title("你跟AI高手，prompt水平差距有多大？（工作日常，非表演）")
        assert result == "你跟AI高手-prompt水平差距有多大-工作日常-非表演"

    def test_sanitize_title_long_title_truncated_before_sanitization(self):
        """Raw title longer than 30 chars is truncated before sanitization."""
        long = "AI 光互连：被 GPU 光芒掩盖的下一个万亿赛道？站在光里的美股｜万字解读光互连 Photonics 产业链｜AXTI｜SOI"
        result = sanitize_title(long)
        # Source is truncated to 30 chars first, so result must be short
        assert len(result) <= 30
        # Should start with the sanitized first 30 chars of the raw title
        assert result.startswith("AI-光互连")

    def test_sanitize_title_cjk_brackets_and_quotes(self):
        assert sanitize_title("标题【重要】：内容") == "标题-重要-内容"

    def test_sanitize_title_cjk_ellipsis_and_middot(self):
        assert sanitize_title("Part1…Part2·Part3") == "Part1-Part2-Part3"


class TestFilenameGeneration:
    """Tests for filename generation."""

    def test_generate_filename_basic(self):
        """Test filename without title: MMDDYYYY_VideoID.txt"""
        filename = generate_filename("01-08-2026", "abc123")
        assert filename == "01082026_abc123.txt"

    def test_generate_filename_with_title(self):
        """Test filename includes sanitized title after video ID."""
        filename = generate_filename("01-08-2026", "abc123", "My Cool Video")
        assert filename == "01082026_abc123_My-Cool-Video.txt"

    def test_generate_filename_with_chinese_title(self):
        """Test filename with Chinese title."""
        filename = generate_filename("12-19-2025", "inXOHNc_UUo", "上市即巅峰 解析SpaceX的机会")
        assert filename == "12192025_inXOHNc_UUo_上市即巅峰-解析SpaceX的机会.txt"

    def test_generate_filename_title_truncated_to_fit(self):
        """Test that a very long title is truncated so total filename stays under 200 chars."""
        long_title = "Word " * 60  # 300 chars of "Word Word..."
        filename = generate_filename("01-08-2026", "abc123", long_title)
        assert len(filename) <= 200
        assert not filename.endswith("-.txt")


class TestJSONOperations:
    """Tests for JSON file operations."""

    def test_load_content_resources(self):
        """Test loading content resources from JSON file."""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            test_data = {
                "content_resources": [
                    {
                        "content_creator": "Test Creator",
                        "native_lang": "en",
                        "content_collection": []
                    }
                ]
            }
            json.dump(test_data, f)
            temp_file = f.name

        try:
            data = load_content_resources(temp_file)
            assert data == test_data
            assert len(data['content_resources']) == 1
            assert data['content_resources'][0]['content_creator'] == "Test Creator"
        finally:
            os.unlink(temp_file)

    def test_save_content_resources(self):
        """Test saving content resources to JSON file."""
        test_data = {
            "content_resources": [
                {
                    "content_creator": "Test Creator",
                    "native_lang": "en",
                    "content_collection": [
                        {
                            "video_id": "test123",
                            "downloaded": True
                        }
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            temp_file = f.name

        try:
            save_content_resources(test_data, temp_file)

            # Verify the file was saved correctly
            with open(temp_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

            assert loaded_data == test_data
            assert loaded_data['content_resources'][0]['content_collection'][0]['downloaded'] == True
        finally:
            os.unlink(temp_file)

    def test_save_and_load_roundtrip(self):
        """Test saving and loading data maintains integrity."""
        test_data = {
            "content_resources": [
                {
                    "content_creator": "海伦子Hellen",
                    "native_lang": "zh",
                    "content_collection": [
                        {
                            "video_title": "Test Video",
                            "video_id": "abc123",
                            "published_time": "12-19-2025",
                            "behind_paywall": False,
                            "downloaded": True
                        }
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            temp_file = f.name

        try:
            save_content_resources(test_data, temp_file)
            loaded_data = load_content_resources(temp_file)
            assert loaded_data == test_data
        finally:
            os.unlink(temp_file)


class TestTranscriptDownload:
    """Tests for transcript download functionality."""

    def test_download_transcript_creates_file(self):
        """Test that download_transcript creates a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")

            # This will likely fail for most test video IDs, but we can test the error handling
            success, error, caption_enabled = download_transcript("invalid_video_id", output_file)

            # We expect this to fail with an invalid video ID
            assert success == False
            assert error is not None
            # caption_enabled can be bool or None (None for unknown status)
            assert caption_enabled is None or isinstance(caption_enabled, bool)

    def test_download_transcript_invalid_video_id(self):
        """Test error handling with invalid video ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error, caption_enabled = download_transcript("", output_file)

            assert success == False
            assert error is not None
            assert isinstance(error, str)
            # caption_enabled can be bool or None (None for unknown status)
            assert caption_enabled is None or isinstance(caption_enabled, bool)


class TestIntegration:
    """Integration tests for the full workflow."""

    def test_filename_generation_workflow(self):
        """Test the complete filename generation workflow with and without titles."""
        test_cases = [
            {
                "published_time": "12-19-2025",
                "video_id": "inXOHNc_UUo",
                "video_title": "上市即巅峰 解析SpaceX的机会",
                "expected": "12192025_inXOHNc_UUo_上市即巅峰-解析SpaceX的机会.txt"
            },
            {
                "published_time": "06-14-2025",
                "video_id": "t7XX6-pon8M",
                "video_title": None,
                "expected": "06142025_t7XX6-pon8M.txt"
            }
        ]

        for case in test_cases:
            result = generate_filename(
                case["published_time"],
                case["video_id"],
                case["video_title"],
            )
            assert result == case["expected"], f"Expected {case['expected']}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
