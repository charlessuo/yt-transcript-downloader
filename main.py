import json
import os
import re
import argparse
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
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


def download_transcript(video_id, output_filename, native_lang=None):
    """Download transcript for a given video ID using YouTube Transcript API.

    Returns:
        tuple: (success: bool, error_message: str|None, caption_enabled: bool|None)
              caption_enabled is True if captions exist, False if disabled, None if unknown
    """
    try:
        # Create API instance
        ytt_api = YouTubeTranscriptApi()

        # Try to get transcript in native language if specified
        if native_lang:
            try:
                transcript_list = ytt_api.list(video_id)
                transcript = transcript_list.find_transcript([native_lang])
                transcript_data = transcript.fetch()
            except Exception:
                # Fallback to any available transcript
                transcript_data = ytt_api.fetch(video_id)
        else:
            transcript_data = ytt_api.fetch(video_id)

        # Write transcript to file
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                for entry in transcript_data:
                    text = entry.text
                    start_time = entry.start
                    duration = entry.duration
                    f.write(f"[{start_time:.2f}s - {start_time + duration:.2f}s] {text}\n")
        except IOError as e:
            # Transcript was successfully fetched, so captions ARE enabled
            # The failure is a local file system issue
            return False, f"Failed to write file: {str(e)}", True

        return True, None, True
    except Exception as e:
        error_message = str(e)
        # Check if error is due to disabled subtitles
        caption_disabled = "Subtitles are disabled" in error_message
        # For non-caption errors, return None to indicate unknown status
        caption_status = False if caption_disabled else None
        return False, error_message, caption_status


def download_single_video(video_id, output_dir="transcripts", creator_name=None,
                         published_time=None, native_lang=None, video_title=None):
    """Download a single YouTube video transcript on-demand.

    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
        output_dir: Directory to save transcript (default: 'transcripts')
        creator_name: Optional creator name for filename (default: 'YouTube')
        published_time: Optional publish date in MM-DD-YYYY format (default: today's date)
        native_lang: Optional native language code (e.g., 'zh', 'en')
        video_title: Optional video title for display

    Returns:
        bool: True if successful, False otherwise
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Set defaults
    if creator_name is None:
        creator_name = "YouTube"
    if published_time is None:
        published_time = datetime.now().strftime("%m-%d-%Y")
    if video_title is None:
        video_title = f"Video {video_id}"

    # Generate filename
    filename = generate_filename(published_time, creator_name, video_id)
    output_path = os.path.join(output_dir, filename)

    # Download transcript
    print(f"Downloading: {video_title}")
    print(f"  Video ID: {video_id}")
    print(f"  Filename: {filename}")

    success, error, caption_enabled = download_transcript(video_id, output_path, native_lang)

    if success:
        print(f"  ✓ Success")
        print(f"\nTranscript saved to: {output_path}")
        return True
    else:
        print(f"  ✗ Failed: {error}")
        return False


def main():
    """
    Main function to download YouTube transcripts.

    Reads content_resources.json, downloads transcripts for each video,
    and updates the JSON with download status.
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
            total_videos += 1
            video_id = video['video_id']
            video_title = video['video_title']
            published_time = video['published_time']

            # Generate filename
            filename = generate_filename(published_time, creator_name, video_id)
            output_path = os.path.join(output_dir, filename)

            # Check if already downloaded via native API
            if video.get('downloaded_via_native_api', False) and os.path.exists(output_path):
                print(f"✓ Already downloaded: {video_title}")
                already_downloaded += 1
                continue

            # Download transcript using YouTube Transcript API
            print(f"Downloading: {video_title}")
            print(f"  Video ID: {video_id}")
            print(f"  Filename: {filename}")

            success, error, caption_enabled = download_transcript(video_id, output_path, native_lang)

            if success:
                print(f"  ✓ Success")
                video['downloaded_via_native_api'] = True
                video['caption_enabled'] = True
                try:
                    save_content_resources(data)
                except Exception as e:
                    print(f"  ⚠️  Warning: Failed to update JSON: {e}")
                successful_downloads += 1
            else:
                print(f"  ✗ Failed: {error}")
                video['downloaded_via_native_api'] = False
                # Only set caption_enabled if we have a definitive value (not None)
                if caption_enabled is not None:
                    video['caption_enabled'] = caption_enabled
                try:
                    save_content_resources(data)
                except Exception as e:
                    print(f"  ⚠️  Warning: Failed to update JSON: {e}")
                failed_downloads += 1

    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total videos: {total_videos}")
    print(f"Already downloaded (skipped): {already_downloaded}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Failed downloads: {failed_downloads}")
    print(f"\nTranscripts saved to: {output_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download YouTube video transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all videos from content_resources.json
  python main.py

  # Download a single video (minimal)
  python main.py --video-id dQw4w9WgXcQ

  # Download with custom options
  python main.py --video-id dQw4w9WgXcQ --creator "Rick Astley" --lang en --date 10-25-1987

  # Download to custom directory
  python main.py --video-id dQw4w9WgXcQ --output-dir my_transcripts
        """
    )

    parser.add_argument(
        '--video-id',
        type=str,
        help='YouTube video ID to download (e.g., dQw4w9WgXcQ). If provided, downloads single video instead of batch.'
    )
    parser.add_argument(
        '--creator',
        type=str,
        help='Content creator name (default: "YouTube")'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Published date in MM-DD-YYYY format (default: today\'s date)'
    )
    parser.add_argument(
        '--lang',
        type=str,
        help='Native language code (e.g., zh, en, ja)'
    )
    parser.add_argument(
        '--title',
        type=str,
        help='Video title for display purposes'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='transcripts',
        help='Output directory for transcripts (default: transcripts)'
    )

    args = parser.parse_args()

    # Single video mode
    if args.video_id:
        success = download_single_video(
            video_id=args.video_id,
            output_dir=args.output_dir,
            creator_name=args.creator,
            published_time=args.date,
            native_lang=args.lang,
            video_title=args.title
        )
        exit(0 if success else 1)
    # Batch mode
    else:
        main()
