import argparse
import time
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .core import OrganizerEngine

class WatcherHandler(FileSystemEventHandler):
    def __init__(self, engine):
        self.engine = engine

    def on_created(self, event):
        if not event.is_directory:
            # Small delay to ensure file write is complete
            time.sleep(1)
            print(f"Detected new file: {event.src_path}")
            self.engine.process_file(Path(event.src_path))

def main():
    parser = argparse.ArgumentParser(description="Smart File Organizer Tool")
    
    parser.add_argument("--path", type=str, default=".", help="Target folder to organize")
    parser.add_argument("--dry-run", action="store_true", help="Simulate organization without moving files")
    parser.add_argument("--undo", action="store_true", help="Undo the last organization batch")
    parser.add_argument("--watch", action="store_true", help="Run in background and monitor for new files")

    args = parser.parse_args()
    target_path = Path(args.path).resolve()

    engine = OrganizerEngine(target_path, dry_run=args.dry_run)

    if args.undo:
        engine.undo_last_operation()
        sys.exit(0)

    if args.watch:
        print(f"Started Watchdog on: {target_path}")
        print("Press Ctrl+C to stop.")
        event_handler = WatcherHandler(engine)
        observer = Observer()
        observer.schedule(event_handler, str(target_path), recursive=False)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    else:
        # Standard One-Time Run
        print(f"Scanning: {target_path}...")
        for item in target_path.iterdir():
            if item.is_file():
                engine.process_file(item)
        print("Done.")

if __name__ == "__main__":
    main()