import json
import os
import tempfile
import pytest
from datetime import datetime
from main import (
    format_date,
    sanitize_creator_name,
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


class TestFilenameGeneration:
    """Tests for filename generation."""

    def test_generate_filename_basic(self):
        """Test basic filename generation."""
        filename = generate_filename("01-08-2026", "Test Creator", "abc123")
        assert filename == "01082026_Test_Creator_abc123.txt"

    def test_generate_filename_chinese_creator(self):
        """Test filename with Chinese creator name."""
        filename = generate_filename("12-19-2025", "海伦子Hellen", "inXOHNc_UUo")
        assert filename == "12192025_海伦子Hellen_inXOHNc_UUo.txt"

    def test_generate_filename_creator_with_multiple_words(self):
        """Test filename with multi-word creator name."""
        filename = generate_filename("06-14-2025", "Money or Life 美股频道", "t7XX6-pon8M")
        assert filename == "06142025_Money_or_Life_美股频道_t7XX6-pon8M.txt"


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
            success, error = download_transcript("invalid_video_id", output_file)

            # We expect this to fail with an invalid video ID
            assert success == False
            assert error is not None

    def test_download_transcript_invalid_video_id(self):
        """Test error handling with invalid video ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript("", output_file)

            assert success == False
            assert error is not None
            assert isinstance(error, str)


class TestIntegration:
    """Integration tests for the full workflow."""

    def test_filename_generation_workflow(self):
        """Test the complete filename generation workflow."""
        test_cases = [
            {
                "published_time": "12-19-2025",
                "creator_name": "海伦子Hellen",
                "video_id": "inXOHNc_UUo",
                "expected": "12192025_海伦子Hellen_inXOHNc_UUo.txt"
            },
            {
                "published_time": "06-14-2025",
                "creator_name": "Money or Life 美股频道",
                "video_id": "t7XX6-pon8M",
                "expected": "06142025_Money_or_Life_美股频道_t7XX6-pon8M.txt"
            }
        ]

        for case in test_cases:
            result = generate_filename(
                case["published_time"],
                case["creator_name"],
                case["video_id"]
            )
            assert result == case["expected"], f"Expected {case['expected']}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
