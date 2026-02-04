"""
Journal Watcher - Monitors Elite Dangerous game logs
This module monitors the Journal files for new events
"""
import json
import os
import time
from pathlib import Path
from typing import Callable, Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class JournalFileHandler(FileSystemEventHandler):
    """
    Handles file modification events for Elite Dangerous Journal files
    """

    def __init__(self, callback: Callable[[Dict], None]):
        """
        Initialize the journal file handler

        Args:
            callback: Function to call when a new event is detected
        """
        super().__init__()
        self.callback = callback
        self.last_position = 0
        self.current_journal: Optional[Path] = None
        self.loading_initial_state = False  # Track if we're loading initial state

    def set_journal_file(self, journal_path: Path, read_initial: bool = False) -> None:
        """
        Set the current journal file to monitor

        Args:
            journal_path: Path to the journal file
            read_initial: If True, read existing events from the file to populate initial state
        """
        if self.current_journal != journal_path:
            self.current_journal = journal_path
            # Reset position for new file
            if journal_path.exists():
                # If read_initial is True, read recent state events from the file
                if read_initial:
                    self._read_initial_state()
                # Set position to end for new events
                self.last_position = journal_path.stat().st_size
            else:
                self.last_position = 0

    def on_modified(self, event) -> None:
        """
        Called when a file is modified

        Args:
            event: File modified event from watchdog
        """
        # Only process if it's the current journal file
        if event.is_directory:
            return

        event_path = Path(event.src_path)

        # Check if this is our journal file
        if self.current_journal and event_path == self.current_journal:
            self._read_new_events()

    def _read_new_events(self) -> None:
        """
        Read new events from the journal file since last read
        """
        if not self.current_journal or not self.current_journal.exists():
            return

        try:
            with open(self.current_journal, 'r', encoding='utf-8', errors='ignore') as f:
                # Seek to last position
                f.seek(self.last_position)

                # Read new lines
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event_data = json.loads(line)
                            self.callback(event_data)
                        except json.JSONDecodeError:
                            # Skip malformed JSON lines
                            continue

                # Update position
                self.last_position = f.tell()

        except (IOError, OSError) as e:
            print(f"Error reading journal file: {e}")

    def _read_initial_state(self) -> None:
        """
        Read recent state-relevant events from the journal file to populate initial game state
        Only reads events that affect game state (LoadGame, FSDJump, Docked, etc.)
        """
        if not self.current_journal or not self.current_journal.exists():
            return

        # Events that affect game state (in order of importance)
        state_events = [
            "LoadGame",  # Most important - contains starting system
            "FSDJump",   # Last jump tells us current system
            "Docked",    # Current docking status
            "Undocked",
            "SupercruiseEntry",
            "SupercruiseExit",
            "ShipRefuelled",
            "ShieldState",
            "Cargo"
        ]

        # Set flag to indicate we're loading initial state (prevents speaking individual events)
        self.loading_initial_state = True

        # Read from the end to find the most recent state events
        try:
            events_found = []
            with open(self.current_journal, 'r', encoding='utf-8', errors='ignore') as f:
                # Read all lines (could be large, but only on startup)
                lines = f.readlines()

                # Process in reverse to get most recent events first
                for line in reversed(lines):
                    line = line.strip()
                    if line:
                        try:
                            event_data = json.loads(line)
                            event_name = event_data.get("event", "")

                            # Only process state-relevant events
                            if event_name in state_events:
                                events_found.append(event_data)

                                # Stop once we have LoadGame (our starting point)
                                if event_name == "LoadGame":
                                    break

                        except json.JSONDecodeError:
                            continue

            # Now process events in forward order (since we collected them in reverse)
            for event_data in reversed(events_found):
                event_name = event_data.get("event", "")
                print(f"[INITIAL STATE] Loading: {event_name}")
                # Mark event as silent so GUI doesn't speak it
                event_data["_initial_state_loading"] = True
                # These will update game state silently
                self.callback(event_data)

            # Send a special event to trigger the summary announcement
            self.callback({
                "event": "InitialStateLoaded",
                "timestamp": "",
                "_initial_state_summary": True
            })

            # Clear the flag
            self.loading_initial_state = False

        except (IOError, OSError) as e:
            print(f"Error reading initial state from journal: {e}")
            self.loading_initial_state = False


class JournalWatcher:
    """
    Main journal watcher class that monitors Elite Dangerous logs
    """

    def __init__(self, journal_dir: str, event_callback: Callable[[Dict], None]):
        """
        Initialize the journal watcher

        Args:
            journal_dir: Path to the Elite Dangerous Journal directory
            event_callback: Function to call when a new event is detected
        """
        self.journal_dir = Path(journal_dir)
        self.event_callback = event_callback
        self.observer: Optional[Observer] = None
        self.handler: Optional[JournalFileHandler] = None
        self.is_running = False

    def _find_latest_journal(self) -> Optional[Path]:
        """
        Find the latest (most recently modified) Journal file

        Returns:
            Path to the latest journal file, or None if no journals found
        """
        if not self.journal_dir.exists():
            print(f"Journal directory does not exist: {self.journal_dir}")
            return None

        # Find all Journal.*.log files
        journal_files = list(self.journal_dir.glob("Journal.*.log"))

        if not journal_files:
            print(f"No journal files found in: {self.journal_dir}")
            return None

        # Sort by modification time, get the latest
        latest_journal = max(journal_files, key=lambda p: p.stat().st_mtime)
        return latest_journal

    def start(self, read_initial_state: bool = True) -> bool:
        """
        Start monitoring the journal file

        Args:
            read_initial_state: If True, read existing events to populate initial game state

        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            return True

        # Find the latest journal file
        latest_journal = self._find_latest_journal()
        if not latest_journal:
            return False

        print(f"Monitoring journal: {latest_journal.name}")

        # Create handler and observer
        self.handler = JournalFileHandler(self.event_callback)
        self.handler.set_journal_file(latest_journal, read_initial=read_initial_state)

        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.journal_dir), recursive=False)
        self.observer.start()

        self.is_running = True
        return True

    def stop(self) -> None:
        """
        Stop monitoring the journal file
        """
        if not self.is_running:
            return

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None

        self.is_running = False

    def check_for_new_journal(self) -> bool:
        """
        Check if a newer journal file has been created (e.g., new game session)
        This should be called periodically

        Returns:
            True if switched to a new journal file
        """
        latest_journal = self._find_latest_journal()
        if not latest_journal:
            return False

        if self.handler and self.handler.current_journal != latest_journal:
            print(f"Switching to new journal: {latest_journal.name}")
            self.handler.set_journal_file(latest_journal)
            return True

        return False

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


def test_journal_watcher():
    """
    Simple test function to verify journal watching works
    """
    import sys

    # Default journal path
    journal_path = os.path.expanduser("~\\Saved Games\\Frontier Developments\\Elite Dangerous")

    if len(sys.argv) > 1:
        journal_path = sys.argv[1]

    def on_event(event_data: Dict):
        event_name = event_data.get("event", "Unknown")
        print(f"Event Detected: {event_name}")

    print(f"Watching journals in: {journal_path}")
    print("Press Ctrl+C to stop...")

    watcher = JournalWatcher(journal_path, on_event)

    try:
        if watcher.start():
            # Keep running and check for new journals periodically
            while True:
                time.sleep(60)  # Check every minute
                watcher.check_for_new_journal()
        else:
            print("Failed to start journal watcher")
    except KeyboardInterrupt:
        print("\nStopping...")
        watcher.stop()


if __name__ == "__main__":
    test_journal_watcher()
