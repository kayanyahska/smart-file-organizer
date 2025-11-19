import os
import shutil
import json
import time
import hashlib
import re
from pathlib import Path
from datetime import datetime

# File to store operation history for the Undo feature
HISTORY_FILE = Path(".organizer_history.json")

class OrganizerEngine:
    def __init__(self, source_dir, dry_run=False):
        self.source = Path(source_dir).resolve()
        self.dry_run = dry_run
        
        # 1. SMART CATEGORIES (Specific Keywords)
        self.rules = {
            "Resumes": ["resume", "cv", "bio", "profile", "curriculum"],
            "Invoices": ["invoice", "bill", "receipt", "payment"],
            "Transcripts": ["transcript", "marksheet", "grade", "score"],
            "Contracts": ["agreement", "contract", "offer", "nda"],
            "Tax_Docs": ["w2", "1099", "tax", "return"]
        }
        
        # 2. MEDIA TYPES (Extensions)
        self.media_exts = {
            "Images": [".jpg", ".jpeg", ".png", ".heic", ".gif", ".webp"],
            "Videos": [".mp4", ".mov", ".avi", ".mkv", ".flv"],
            "Audio":  [".mp3", ".wav", ".aac", ".m4a", ".flac"], # Added .m4a
            "Archives": [".zip", ".rar", ".7z", ".dmg", ".iso"]   # Added .dmg
        }

        # 3. FALLBACK GROUPS (Group specific extensions together)
        self.fallback_groups = {
            "Misc_Notebooks": [".ipynb"],
            "Misc_Presentations": [".ppt", ".pptx", ".key", ".odp"],
            "Misc_Documents": [".doc", ".docx", ".odt", ".rtf", ".txt"],
            "Misc_Spreadsheets": [".xls", ".xlsx", ".csv"]
        }

    def _calculate_hash(self, file_path):
        """Generates SHA-256 hash of a file to verify content uniqueness."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read in 4KB chunks to avoid memory issues with large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""

    def _get_category(self, file_path):
        """Determines category based on extension, keywords, or extension grouping."""
        name = file_path.name.lower()
        ext = file_path.suffix.lower()

        # A. Check Media Extensions first
        for cat, extensions in self.media_exts.items():
            if ext in extensions:
                return cat

        # B. Check Document Keywords (Resumes, Invoices, etc.)
        for cat, keywords in self.rules.items():
            if any(k in name for k in keywords):
                return cat

        # C. Check Fallback Groups (Notebooks, Presentations, etc.)
        for group_name, extensions in self.fallback_groups.items():
            if ext in extensions:
                return group_name

        # D. FINAL FALLBACK: Group by generic extension
        # Example: .xyz -> "Misc_XYZ"
        if ext:
            clean_ext = ext.lstrip('.').upper()
            return f"Misc_{clean_ext}"
        
        return "Misc_Files"

    def _log_move(self, src, dst):
        """Saves the move operation to a JSON file for Undoing."""
        entry = {"src": str(src), "dst": str(dst), "timestamp": time.time()}
        
        history = []
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                pass 
        
        history.append(entry)
        
        if not self.dry_run:
            with open(HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=4)

    def process_file(self, file_path):
        """Main logic: Categorize -> Check Duplicates -> Rename -> Move."""
        
        # Initialize a memory for Dry Run so it doesn't reuse names
        if not hasattr(self, 'simulated_files'):
            self.simulated_files = set()

        # Skip directories or hidden files
        if file_path.is_dir() or file_path.name.startswith("."):
            return

        # 1. Identify Category & Target Folder
        category = self._get_category(file_path)
        target_dir = self.source / category
        target_dir.mkdir(exist_ok=True)

        # 2. Check for CONTENT Duplicates (Hashing)
        # Note: In Dry Run, we can only check against REAL files, not simulated ones
        current_hash = self._calculate_hash(file_path)
        is_duplicate = False

        for existing_file in target_dir.iterdir():
            if existing_file.is_file():
                if self._calculate_hash(existing_file) == current_hash:
                    is_duplicate = True
                    print(f"[DUPLICATE] {file_path.name} is identical to {existing_file.name}")
                    break
        
        # 3. Decision: Move to Category OR Move to Quarantine
        if is_duplicate:
            duplicate_dir = self.source / "Duplicates"
            duplicate_dir.mkdir(exist_ok=True)
            
            dest = duplicate_dir / file_path.name
            idx = 1
            # Check against REAL files OR SIMULATED files
            while dest.exists() or (self.dry_run and str(dest) in self.simulated_files):
                dest = duplicate_dir / f"Duplicate_{idx}_{file_path.name}"
                idx += 1
                
            if not self.dry_run:
                shutil.move(str(file_path), str(dest))
                self._log_move(file_path, dest)
            else:
                self.simulated_files.add(str(dest)) # Remember this fake move
            
            print(f"  -> Quarantined: Duplicates/{dest.name}")
            
        else:
            # 4. Normal Processing (Rename by Date & Sequence)
            timestamp = file_path.stat().st_ctime
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            
            # Logic: Resumes -> Resume_Date_01.pdf
            prefix = category
            if category == "Images": prefix = "Img"
            elif category == "Videos": prefix = "Vid"
            elif category == "Audio": prefix = "Aud"
            elif category.endswith('s') and len(category) > 4: prefix = category[:-1]

            idx = 1
            new_name = f"{prefix}_{date_str}_{idx:02d}{file_path.suffix}"
            dest = target_dir / new_name

            # Collision handling: Check REAL file AND SIMULATED file
            while dest.exists() or (self.dry_run and str(dest) in self.simulated_files):
                idx += 1
                new_name = f"{prefix}_{date_str}_{idx:02d}{file_path.suffix}"
                dest = target_dir / new_name
            
            if not self.dry_run:
                shutil.move(str(file_path), str(dest))
                self._log_move(file_path, dest)
            else:
                self.simulated_files.add(str(dest)) # Remember this fake move

            print(f"  -> Moved: {category}/{new_name}")

    def undo_last_operation(self):
        """Reverses the moves recorded in history."""
        if not HISTORY_FILE.exists():
            print("No history found.")
            return

        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)

        if not history:
            print("History is empty.")
            return

        print(f"--- Undoing {len(history)} operations ---")
        
        # Reverse list to undo latest first
        for entry in reversed(history):
            src = Path(entry['src'])
            dst = Path(entry['dst'])

            if dst.exists():
                print(f"Restoring: {dst.name} -> {src.name}")
                if not self.dry_run:
                    shutil.move(str(dst), str(src))
                    # Clean up empty folders
                    if not any(dst.parent.iterdir()):
                        try:
                            dst.parent.rmdir()
                        except:
                            pass
            else:
                print(f"Warning: File {dst} not found. Cannot restore.")

        # Clear history file
        if not self.dry_run:
            os.remove(HISTORY_FILE)