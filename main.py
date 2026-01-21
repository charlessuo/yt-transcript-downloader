import json
import os
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi


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
    date_obj = datetime.strptime(published_time, "%m-%d-%Y")
    return date_obj.strftime("%m%d%Y")


def sanitize_creator_name(creator_name):
    """Replace spaces with underscores in creator name."""
    return creator_name.replace(" ", "_")


def generate_filename(published_time, creator_name, video_id):
    """Generate filename in format: MMDDYYYY_CreatorName_VideoID.txt"""
    date_str = format_date(published_time)
    creator_str = sanitize_creator_name(creator_name)
    return f"{date_str}_{creator_str}_{video_id}.txt"


def download_transcript(video_id, output_filename, native_lang=None):
    """Download transcript for a given video ID."""
    try:
        # Try to get transcript in native language if specified
        if native_lang:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = transcript_list.find_transcript([native_lang])
                transcript_data = transcript.fetch()
            except:
                # Fallback to any available transcript
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        else:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)

        # Write transcript to file
        with open(output_filename, 'w', encoding='utf-8') as f:
            for entry in transcript_data:
                text = entry['text']
                start_time = entry['start']
                duration = entry['duration']
                f.write(f"[{start_time:.2f}s - {start_time + duration:.2f}s] {text}\n")

        return True, None
    except Exception as e:
        return False, str(e)


def main():
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

            # Check if already downloaded (from JSON flag)
            if video.get('downloaded', False):
                print(f"✓ Already downloaded (marked in JSON): {video_title}")
                already_downloaded += 1
                continue

            # Generate filename
            filename = generate_filename(published_time, creator_name, video_id)
            output_path = os.path.join(output_dir, filename)

            # Download transcript
            print(f"Downloading: {video_title}")
            print(f"  Video ID: {video_id}")
            print(f"  Filename: {filename}")

            success, error = download_transcript(video_id, output_path, native_lang)

            if success:
                print(f"  ✓ Success")
                # Update JSON to mark as downloaded
                video['downloaded'] = True
                save_content_resources(data)
                successful_downloads += 1
            else:
                print(f"  ✗ Failed: {error}")
                video['downloaded'] = False
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
    main()
