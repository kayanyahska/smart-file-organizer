# Smart File Organizer

A sophisticated Python automation tool that organizes cluttered directories based on file types, content analysis, and custom rules.

## Features
- **Smart Sorting:** Automatically sorts PDFs, Images, Videos, and Documents.
- **Content Safety:** Uses SHA-256 Hashing to detect duplicates before moving.
- **Undo Capability:** Transaction logs allow you to revert changes instantly.
- **Dry Run:** Preview changes before they happen.
- **Watchdog Mode:** Monitors folders in real-time for new downloads.

## Installation
```bash
pip install -e .

# Organize a folder
organize --path "pathname"

# Run safely (Simulation)
organize --path "pathname" --dry-run

# Undo last operation
organize --undo