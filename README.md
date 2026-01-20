# YouTube Transcript Downloader

A Python project for downloading YouTube transcripts.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) - Fast Python package manager

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

### 2. Run the Application

```bash
uv run main.py
```

### 3. Using the Virtual Environment

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

### 4. Adding New Dependencies

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
