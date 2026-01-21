# YouTube Transcript Downloader

A Python project for downloading YouTube transcripts using two different approaches:
1. **Native API** (YouTube Transcript API) - Free, works with videos that have captions enabled
2. **Supadata API** - Paid service, can generate transcripts for videos without captions

## Prerequisites

- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- (Optional) [Supadata API Key](https://supadata.ai/) - Required for downloading videos without captions

### Installing uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

## Getting Started

### 1. Install Dependencies

```bash
uv sync
```

This will create a virtual environment and install all dependencies from `pyproject.toml`.

### 2. Configure Supadata API Key (Optional - Only for videos without captions)

If you want to use the Supadata API for videos without captions:

1. Get your API key from [Supadata](https://supadata.ai/)
2. Create a `.env` file in the project root
3. Add your API key:

```bash
SUPADATA_API_KEY=your_api_key_here
```

### 3. Run the Application

#### Approach 1: Native API (YouTube Transcript API) - Start Here

Always run this first. Downloads transcripts using YouTube's native API for videos with captions enabled.

```bash
uv run main.py
```

**Updates JSON flags:**
- `downloaded_via_native_api`: `true` if successful
- `caption_enabled`: `true` if captions exist, `false` if not

#### Approach 2: Supadata API (Optional - Only for videos without captions)

**Only run this if you have videos where:**
- `caption_enabled` is `false` (no YouTube captions available)
- `downloaded_via_supadata` is `false` (not yet downloaded via Supadata)

This approach uses AI to generate transcripts for videos without captions (requires paid API key).

```bash
uv run main_supadata.py
```

**Updates JSON flags:**
- `downloaded_via_supadata`: `true` if successful

**Recommended Workflow:**
1. Run `uv run main.py` first (native API - free)
2. Check which videos failed due to `caption_enabled: false`
3. If needed, run `uv run main_supadata.py` (paid API) to download those specific videos

### 4. Using the Virtual Environment

After running `uv sync`, a virtual environment is created in `.venv` with Python 3.13. You have two options to use it:

#### Option 1: Use `uv run` (Recommended)
This automatically uses the virtual environment without manual activation:

```bash
# Check Python version
uv run python --version

# Run your script
uv run main.py

# Run any Python command
uv run python -c "print('Hello')"
```

#### Option 2: Manually Activate the Virtual Environment
If you want to activate it for your current shell session:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Now you can use Python directly
python --version  # Should show 3.13.5
python main.py

# When done, deactivate
deactivate
```

### 5. Adding New Dependencies

```bash
# Add a regular dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Example: Add YouTube transcript API
uv add youtube-transcript-api
```

## Common uv Commands

```bash
# Install dependencies from pyproject.toml
uv sync

# Run a Python script
uv run <script.py>

# Run a Python command
uv run python -c "print('Hello')"

# Add a package
uv add <package-name>

# Remove a package
uv remove <package-name>

# Update all packages
uv lock --upgrade

# Show installed packages
uv pip list

# Create a lock file
uv lock
```

## Project Structure

```
yt-transcript-downloader/
├── .python-version      # Python version specification (3.13)
├── pyproject.toml       # Project configuration and dependencies
├── main.py             # Main application entry point
└── README.md           # This file
```

## Development

This project uses Python 3.13 and uv for dependency management. The virtual environment is automatically managed by uv.

## JSON Flags

The `content_resources.json` file tracks the following flags for each video:

- `downloaded_via_native_api` (boolean) - `true` if successfully downloaded via YouTube API
- `downloaded_via_supadata` (boolean) - `true` if successfully downloaded via Supadata API
- `caption_enabled` (boolean) - `true` if video has YouTube captions, `false` if not
- `behind_paywall` (boolean) - Video access status

## Two Approaches

### main.py (Native YouTube API)
- Free
- Works only with videos that have captions enabled
- Always run this first
- Updates: `downloaded_via_native_api` and `caption_enabled`

### main_supadata.py (Supadata AI API)
- Paid API (requires API key)
- Generates transcripts for videos without captions
- Only processes videos where `caption_enabled = false` and `downloaded_via_supadata = false`
- Updates: `downloaded_via_supadata`
