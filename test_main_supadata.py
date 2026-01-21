import json
import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from main_supadata import (
    format_date,
    sanitize_creator_name,
    generate_filename,
    download_transcript_via_supadata,
    load_content_resources,
    save_content_resources
)


class TestSupadataDownload:
    """Tests for Supadata API download functionality."""

    @patch('main_supadata.os.getenv')
    def test_download_transcript_via_supadata_no_api_key(self, mock_getenv):
        """Test that missing API key returns appropriate error."""
        mock_getenv.return_value = None

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == False
            assert "SUPADATA_API_KEY not found" in error

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    def test_download_transcript_via_supadata_immediate_success(self, mock_getenv, mock_requests_get):
        """Test successful immediate response (HTTP 200) from Supadata API."""
        mock_getenv.return_value = "test_api_key"

        # Mock successful immediate response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "This is a test transcript content."
        mock_requests_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == True
            assert error is None

            # Verify file was created with correct content
            assert os.path.exists(output_file)
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == "This is a test transcript content."

            # Verify API was called with correct parameters
            mock_requests_get.assert_called_once()
            call_args = mock_requests_get.call_args
            assert "https://api.supadata.ai/v1/transcript" in call_args[0]
            assert call_args[1]['params']['url'].startswith('https://www.youtube.com/watch?v=')
            assert call_args[1]['params']['text'] == "true"
            assert call_args[1]['headers']['x-api-key'] == "test_api_key"

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    @patch('main_supadata.time.sleep')  # Mock sleep to speed up tests
    def test_download_transcript_via_supadata_job_completion(self, mock_sleep, mock_getenv, mock_requests_get):
        """Test successful job completion (HTTP 202 -> job polling -> completion)."""
        mock_getenv.return_value = "test_api_key"

        # Mock initial 202 response with job ID
        mock_initial_response = Mock()
        mock_initial_response.status_code = 202
        mock_initial_response.json.return_value = {"jobId": "test_job_123"}

        # Mock job status check responses
        mock_active_response = Mock()
        mock_active_response.status_code = 200
        mock_active_response.json.return_value = {"status": "active"}

        mock_completed_response = Mock()
        mock_completed_response.status_code = 200
        mock_completed_response.json.return_value = {
            "status": "completed",
            "content": "Final transcript content from job."
        }

        # Set up the mock to return different responses on successive calls
        mock_requests_get.side_effect = [
            mock_initial_response,  # Initial request
            mock_active_response,    # First status check
            mock_completed_response  # Second status check
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == True
            assert error is None

            # Verify file was created with correct content
            assert os.path.exists(output_file)
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == "Final transcript content from job."

            # Verify multiple API calls were made
            assert mock_requests_get.call_count == 3

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    @patch('main_supadata.time.sleep')
    def test_download_transcript_via_supadata_job_with_list_content(self, mock_sleep, mock_getenv, mock_requests_get):
        """Test job completion with structured list content instead of plain text."""
        mock_getenv.return_value = "test_api_key"

        # Mock initial 202 response
        mock_initial_response = Mock()
        mock_initial_response.status_code = 202
        mock_initial_response.json.return_value = {"jobId": "test_job_456"}

        # Mock completed response with list content
        mock_completed_response = Mock()
        mock_completed_response.status_code = 200
        mock_completed_response.json.return_value = {
            "status": "completed",
            "content": [
                {"text": "First segment of transcript."},
                {"text": "Second segment of transcript."},
                {"text": "Third segment of transcript."}
            ]
        }

        mock_requests_get.side_effect = [
            mock_initial_response,
            mock_completed_response
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == True
            assert error is None

            # Verify file content
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "First segment of transcript." in content
            assert "Second segment of transcript." in content
            assert "Third segment of transcript." in content

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    @patch('main_supadata.time.sleep')
    def test_download_transcript_via_supadata_job_failed(self, mock_sleep, mock_getenv, mock_requests_get):
        """Test handling of failed job status."""
        mock_getenv.return_value = "test_api_key"

        # Mock initial 202 response
        mock_initial_response = Mock()
        mock_initial_response.status_code = 202
        mock_initial_response.json.return_value = {"jobId": "test_job_789"}

        # Mock failed job response
        mock_failed_response = Mock()
        mock_failed_response.status_code = 200
        mock_failed_response.json.return_value = {"status": "failed"}

        mock_requests_get.side_effect = [
            mock_initial_response,
            mock_failed_response
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == False
            assert "Supadata job failed" in error

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    def test_download_transcript_via_supadata_api_error(self, mock_getenv, mock_requests_get):
        """Test handling of API error responses."""
        mock_getenv.return_value = "test_api_key"

        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = '{"error":"limit-exceeded"}'
        mock_requests_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == False
            assert "429" in error

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    def test_download_transcript_via_supadata_network_error(self, mock_getenv, mock_requests_get):
        """Test handling of network errors."""
        mock_getenv.return_value = "test_api_key"

        # Mock network error
        import requests
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Network error")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == False
            assert "Network error" in error

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    def test_download_transcript_via_supadata_with_language(self, mock_getenv, mock_requests_get):
        """Test that language parameter is passed correctly."""
        mock_getenv.return_value = "test_api_key"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Transcript in specified language."
        mock_requests_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file, native_lang="zh")

            assert success == True

            # Verify language parameter was passed
            call_args = mock_requests_get.call_args
            assert call_args[1]['params']['lang'] == "zh"

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    def test_download_transcript_via_supadata_empty_response(self, mock_getenv, mock_requests_get):
        """Test handling of empty HTTP 200 response."""
        mock_getenv.return_value = "test_api_key"

        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_requests_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == False
            assert "empty response" in error.lower()

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    def test_download_transcript_via_supadata_whitespace_only_response(self, mock_getenv, mock_requests_get):
        """Test handling of whitespace-only HTTP 200 response."""
        mock_getenv.return_value = "test_api_key"

        # Mock whitespace-only response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "   \n\t  "
        mock_requests_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == False
            assert "empty response" in error.lower()

    @patch('main_supadata.requests.get')
    @patch('main_supadata.os.getenv')
    @patch('main_supadata.time.sleep')
    def test_download_transcript_via_supadata_job_timeout(self, mock_sleep, mock_getenv, mock_requests_get):
        """Test that job polling times out after max attempts."""
        mock_getenv.return_value = "test_api_key"

        # Mock initial 202 response
        mock_initial_response = Mock()
        mock_initial_response.status_code = 202
        mock_initial_response.json.return_value = {"jobId": "test_job_timeout"}

        # Mock active response that never completes
        mock_active_response = Mock()
        mock_active_response.status_code = 200
        mock_active_response.json.return_value = {"status": "active"}

        # Return active status for all polling attempts
        mock_requests_get.side_effect = [mock_initial_response] + [mock_active_response] * 30

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_transcript.txt")
            success, error = download_transcript_via_supadata("test_video_id", output_file)

            assert success == False
            assert "Job timed out" in error


class TestSupadataHelperFunctions:
    """Tests for helper functions used in main_supadata.py."""

    def test_format_date(self):
        """Test date formatting function."""
        assert format_date("01-15-2026") == "01152026"

    def test_sanitize_creator_name(self):
        """Test creator name sanitization."""
        assert sanitize_creator_name("Test Creator") == "Test_Creator"

    def test_generate_filename(self):
        """Test filename generation."""
        filename = generate_filename("12-25-2025", "Test Creator", "abc123")
        assert filename == "12252025_Test_Creator_abc123.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
