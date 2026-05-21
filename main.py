import json
import os
import re
import argparse
import requests
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def extract_video_id(value):
    """Extract a YouTube video ID from a URL or return the value as-is.

    Handles:
      https://www.youtube.com/watch?v=VIDEO_ID (strips extra params like &t=15s)
      https://youtu.be/VIDEO_ID
      https://www.youtube.com/shorts/VIDEO_ID
    """
    parsed = urlparse(value)
    if parsed.scheme in ('http', 'https'):
        if parsed.netloc not in ('www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com'):
            raise argparse.ArgumentTypeError(f"Not a YouTube URL: {value}")
        if parsed.netloc == 'youtu.be':
            video_id = parsed.path.lstrip('/')
        else:
            qs = parse_qs(parsed.query)
            if 'v' in qs:
                video_id = qs['v'][0]
            else:
                # Handle /shorts/VIDEO_ID and /embed/VIDEO_ID
                path_parts = parsed.path.strip('/').split('/')
                if len(path_parts) >= 2 and path_parts[0] in ('shorts', 'embed'):
                    video_id = path_parts[1]
                else:
                    raise argparse.ArgumentTypeError(f"Could not extract video ID from URL: {value}")
        return video_id
    return value


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


def sanitize_title(title, max_length=None):
    """Sanitize video title for use in a filename, with dashes as word separators.

    Whitespace and CJK/Unicode punctuation that acts as a word boundary are
    converted to dashes; remaining invalid filename characters are stripped.
    """
    t = title.strip()
    # Truncate raw title before sanitization so filenames stay manageable.
    if len(t) > 30:
        t = t[:30]
    # Convert whitespace and CJK/Unicode word-boundary punctuation to dashes.
    t = re.sub(
        r'[\s，。、；…·—！？：（）【】『』「」“”‘’《》〈〉～｜]+',
        '-', t,
    )
    # Strip remaining invalid filename characters (ASCII + full-width variants).
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f＜＞：＂／＼｜？＊！]', '', t)
    # Normalize dashes.
    t = re.sub(r'-+', '-', t)
    t = t.strip('-')
    if max_length and len(t) > max_length:
        t = t[:max_length].rstrip('-')
    return t if t else "Untitled"


def fetch_video_metadata(video_id):
    """Fetch video title and upload date from YouTube without an API key.

    Returns:
        dict with optional keys 'title' (str) and 'upload_date' (str, MM-DD-YYYY),
        or None if nothing could be retrieved.
    """
    result = {}

    try:
        resp = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=10,
        )
        if resp.status_code == 200:
            title = resp.json().get("title")
            if title:
                result["title"] = title
    except Exception:
        pass

    try:
        page = requests.get(
            f"https://www.youtube.com/watch?v={video_id}",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=15,
        )
        if page.status_code == 200:
            # YouTube embeds dates as ISO 8601 ("2025-12-19" or "2025-12-19T00:00:00+00:00").
            # Don't require a closing quote so the timestamp suffix doesn't break the match.
            m = re.search(
                r'"(?:publishDate|datePublished|uploadDate)"\s*:\s*"(\d{4}-\d{2}-\d{2})',
                page.text,
            )
            if m:
                y, mo, d = m.group(1).split("-")
                result["upload_date"] = f"{mo}-{d}-{y}"
    except Exception:
        pass

    return result if result else None


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


def generate_filename(published_time, video_id, video_title=None):
    """Generate filename: MMDDYYYY_VideoID[_Video-Title].txt"""
    date_str = format_date(published_time)

    if video_title:
        # Reserve chars for fixed parts so total stays under 200 chars.
        reserved = len(date_str) + 1 + len(video_id) + 1 + len(".txt")
        max_title_len = max(10, 200 - reserved)
        title_str = sanitize_title(video_title, max_length=max_title_len)
        return f"{date_str}_{video_id}_{title_str}.txt"

    return f"{date_str}_{video_id}.txt"


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
            transcript_list = ytt_api.list(video_id)
            # Try exact match first, then prefix match (e.g. 'zh' matches 'zh-Hans')
            transcript = None
            try:
                transcript = transcript_list.find_transcript([native_lang])
            except Exception:
                for t in transcript_list:
                    if t.language_code.startswith(native_lang):
                        transcript = t
                        break
            if transcript is not None:
                transcript_data = transcript.fetch()
            else:
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

    # Fetch upload date and title from YouTube when not provided by the caller
    if published_time is None or video_title is None:
        print(f"  Fetching video metadata...")
        meta = fetch_video_metadata(video_id)
        if meta:
            if published_time is None:
                published_time = meta.get("upload_date")
            if video_title is None:
                video_title = meta.get("title")

    # Fall back to today if the upload date still could not be determined
    if published_time is None:
        print(f"  Warning: could not fetch upload date, using today's date")
        published_time = datetime.now().strftime("%m-%d-%Y")
    if video_title is None:
        video_title = f"Video {video_id}"

    # Generate filename
    filename = generate_filename(published_time, video_id, video_title)
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
            filename = generate_filename(published_time, video_id, video_title)
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

  # Download a single video by ID
  python main.py --video-id dQw4w9WgXcQ

  # Video ID starting with '-': use = to avoid flag ambiguity
  python main.py --video-id=-s9Oj3koBTc

  # Download by YouTube URL — QUOTE watch URLs (? is a shell glob in zsh/bash)
  python main.py --video-id "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  python main.py --video-id "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=15s"
  python main.py --video-id "https://www.youtube.com/watch?v=-s9Oj3koBTc"
  python main.py --video-id https://youtu.be/dQw4w9WgXcQ

  # Download with custom options
  python main.py --video-id dQw4w9WgXcQ --creator "Rick Astley" --lang en --date 10-25-1987

  # Download to custom directory
  python main.py --video-id dQw4w9WgXcQ --output-dir my_transcripts
        """
    )

    parser.add_argument(
        '--video-id',
        type=extract_video_id,
        help='YouTube video ID or URL. For IDs starting with "-", use --video-id=VALUE.'
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
