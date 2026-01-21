import json
import os
import re
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def load_content_resources(file_path="content_resources.json"):
    """Load content resources from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_content_resources(data, file_path="content_resources.json"):
    """Save content resources to JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def format_date(published_time):
    """Convert MM-DD-YYYY to MMDDYYYY format (US style)."""
    try:
        date_obj = datetime.strptime(published_time, "%m-%d-%Y")
        return date_obj.strftime("%m%d%Y")
    except ValueError as e:
        raise ValueError(f"Invalid date format '{published_time}': expected MM-DD-YYYY") from e


def sanitize_creator_name(creator_name):
    """Replace spaces and remove invalid filename characters."""
    # First, strip leading/trailing spaces and periods
    name = creator_name.strip('. ')
    # Replace internal spaces with underscores
    name = name.replace(" ", "_")
    # Remove invalid filename characters (Windows + Unix)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    # Final cleanup: remove any remaining leading/trailing periods or underscores
    name = name.strip('._')
    return name if name else "Unknown"


def generate_filename(published_time, creator_name, video_id):
    """Generate filename in format: MMDDYYYY_CreatorName_VideoID.txt"""
    date_str = format_date(published_time)
    creator_str = sanitize_creator_name(creator_name)
    return f"{date_str}_{creator_str}_{video_id}.txt"


def download_transcript_via_supadata(video_id, output_filename, native_lang=None):
    """Download transcript using Supadata API.

    Returns:
        tuple: (success: bool, error_message: str|None)
    """
    api_key = os.getenv("SUPADATA_API_KEY")

    if not api_key:
        return False, "SUPADATA_API_KEY not found in .env file"

    try:
        # Build API request using full YouTube URL
        url = "https://api.supadata.ai/v1/transcript"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        params = {
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "text": "true"
        }

        # Add language parameter if specified
        if native_lang:
            params["lang"] = native_lang

        # Make API request
        response = requests.get(url, headers=headers, params=params, timeout=30)

        # Handle immediate response (HTTP 200)
        if response.status_code == 200:
            transcript_text = response.text

            # Write transcript to file
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    f.write(transcript_text)
            except IOError as e:
                return False, f"Failed to write file: {str(e)}"

            return True, None

        # Handle job queued (HTTP 202)
        elif response.status_code == 202:
            try:
                job_data = response.json()
                job_id = job_data.get("jobId")

                if not job_id:
                    return False, "Received 202 but no jobId in response"

                print(f"    Job queued: {job_id}. Polling for results...")

                # Poll for job completion (max 90 seconds with 3-second intervals)
                max_attempts = 30
                poll_interval = 3

                for attempt in range(max_attempts):
                    time.sleep(poll_interval)

                    # Check job status
                    job_url = f"https://api.supadata.ai/v1/transcript/{job_id}"
                    job_response = requests.get(job_url, headers=headers, timeout=30)

                    if job_response.status_code != 200:
                        continue

                    job_result = job_response.json()
                    status = job_result.get("status")

                    print(f"    Job status: {status} (attempt {attempt + 1}/{max_attempts})")

                    if status == "completed":
                        content = job_result.get("content")
                        if not content:
                            return False, "Job completed but no content in response"

                        # Write transcript to file
                        try:
                            with open(output_filename, 'w', encoding='utf-8') as f:
                                # Handle both plain text (str) and structured data (list)
                                if isinstance(content, str):
                                    f.write(content)
                                elif isinstance(content, list):
                                    # Structured format with timestamps
                                    for entry in content:
                                        text = entry.get("text", "")
                                        f.write(f"{text}\n")
                                else:
                                    return False, f"Unexpected content type: {type(content)}"
                        except IOError as e:
                            return False, f"Failed to write file: {str(e)}"

                        return True, None

                    elif status == "failed":
                        return False, "Supadata job failed"

                    # Continue polling for "queued" or "active"

                return False, "Job timed out after 90 seconds"

            except Exception as e:
                return False, f"Error polling job: {str(e)}"

        else:
            return False, f"Supadata API error: {response.status_code} - {response.text}"

    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def main():
    """
    Download YouTube transcripts using Supadata API.

    Only processes videos where:
    - caption_enabled is False (no YouTube captions available)
    - downloaded_via_supadata is False (not yet downloaded via Supadata)
    """
    # Create output directory if it doesn't exist
    output_dir = "transcripts"
    os.makedirs(output_dir, exist_ok=True)

    # Load content resources
    print("Loading content resources...")
    data = load_content_resources()

    # Statistics
    total_videos = 0
    successful_downloads = 0
    failed_downloads = 0
    already_downloaded = 0
    skipped_has_captions = 0

    # Process each content creator
    for resource in data['content_resources']:
        creator_name = resource['content_creator']
        native_lang = resource.get('native_lang')
        content_collection = resource['content_collection']

        if not content_collection:
            print(f"\nSkipping '{creator_name}' - no videos in collection")
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {creator_name}")
        print(f"Videos: {len(content_collection)}")
        print(f"{'='*60}")

        for video in content_collection:
            video_id = video['video_id']
            video_title = video['video_title']
            published_time = video['published_time']

            # Check if video has captions enabled
            if video.get('caption_enabled', True):
                # Skip videos that have captions (should use native API)
                skipped_has_captions += 1
                continue

            # Check if already downloaded via Supadata
            if video.get('downloaded_via_supadata', False):
                filename = generate_filename(published_time, creator_name, video_id)
                output_path = os.path.join(output_dir, filename)
                if os.path.exists(output_path):
                    print(f"✓ Already downloaded: {video_title}")
                    already_downloaded += 1
                    continue

            total_videos += 1

            # Generate filename
            filename = generate_filename(published_time, creator_name, video_id)
            output_path = os.path.join(output_dir, filename)

            # Download transcript using Supadata
            print(f"Downloading: {video_title}")
            print(f"  Video ID: {video_id}")
            print(f"  Filename: {filename}")

            success, error = download_transcript_via_supadata(video_id, output_path, native_lang)

            if success:
                print(f"  ✓ Success")
                video['downloaded_via_supadata'] = True
                try:
                    save_content_resources(data)
                except Exception as e:
                    print(f"  ⚠️  Warning: Failed to update JSON: {e}")
                successful_downloads += 1
            else:
                print(f"  ✗ Failed: {error}")
                video['downloaded_via_supadata'] = False
                try:
                    save_content_resources(data)
                except Exception as e:
                    print(f"  ⚠️  Warning: Failed to update JSON: {e}")
                failed_downloads += 1

    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY (Supadata API)")
    print(f"{'='*60}")
    print(f"Videos without captions: {total_videos + already_downloaded}")
    print(f"Videos with captions (skipped): {skipped_has_captions}")
    print(f"Already downloaded (skipped): {already_downloaded}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Failed downloads: {failed_downloads}")
    print(f"\nTranscripts saved to: {output_dir}/")


if __name__ == "__main__":
    main()
