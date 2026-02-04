#!/usr/bin/env python3
"""
Installation helper for pocket-tts
This script installs pocket-tts from the local models/pocket-tts folder
"""
import subprocess
import sys
import os
from pathlib import Path

# Fix console encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def install_pocket_tts():
    """Install pocket-tts from the local folder"""

    print("=" * 60)
    print("EDAI - pocket-tts Installation Helper")
    print("=" * 60)

    # Check if pocket-tts folder exists
    project_root = Path(__file__).parent
    pocket_tts_path = project_root / "models" / "pocket-tts"

    if not pocket_tts_path.exists():
        print(f"\n✗ Error: pocket-tts folder not found at: {pocket_tts_path}")
        print("\nPlease clone the repository first:")
        print("  cd models")
        print("  git clone https://github.com/kyutai-labs/pocket-tts.git")
        return False

    print(f"\n✓ Found pocket-tts at: {pocket_tts_path}")

    # Check if PyTorch is installed
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__} is installed")
    except ImportError:
        print("\n✗ PyTorch is not installed.")
        print("\nInstalling PyTorch (CPU version)...")

        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "torch>=2.5.0", "torchaudio>=2.5.0", "--index-url", "https://download.pytorch.org/whl/cpu"
            ])
            print("✓ PyTorch installed successfully")
        except subprocess.CalledProcessError:
            print("\n✗ Failed to install PyTorch. Please install manually:")
            print("  pip install torch>=2.5.0 torchaudio>=2.5.0")
            return False

    # Install pocket-tts from local folder
    print("\nInstalling pocket-tts from local folder...")

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-e",
            str(pocket_tts_path)
        ])
        print("✓ pocket-tts installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to install pocket-tts: {e}")
        return False

    # Test import
    print("\nTesting pocket-tts import...")
    try:
        from pocket_tts import TTSModel
        print("✓ pocket-tts import successful!")
    except ImportError as e:
        print(f"\n✗ Failed to import pocket-tts: {e}")
        return False

    print("\n" + "=" * 60)
    print("Installation complete!")
    print("=" * 60)
    print("\nYou can now run EDAI with TTS support:")
    print("  python main.py")
    print("\nAvailable voices:")
    print("  - alba (female, default)")
    print("  - marius (male)")
    print("  - javert (male)")
    print("  - jean (male)")
    print("  - fantine (female)")
    print("  - cosette (female)")
    print("  - eponine (female)")
    print("  - azelma (female)")

    return True


if __name__ == "__main__":
    success = install_pocket_tts()
    sys.exit(0 if success else 1)
