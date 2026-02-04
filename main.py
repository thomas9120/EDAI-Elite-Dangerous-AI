#!/usr/bin/env python3
"""
EDAI - Elite Dangerous AI Interface
Main Entry Point

A local AI companion for Elite Dangerous that:
- Monitors the game's journal logs
- Uses a local LLM to generate in-character responses
- Converts responses to speech using local TTS

Usage:
    python main.py

Requirements:
    - Python 3.10+
    - See requirements.txt for dependencies
"""
import sys
import os

# Add src directory to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from src.gui import main as gui_main


def main():
    """Main entry point"""
    try:
        gui_main()
    except KeyboardInterrupt:
        print("\nShutting down EDAI...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
