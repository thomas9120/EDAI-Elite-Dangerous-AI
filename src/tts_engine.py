"""
TTS Engine - The Mouth of EDAI
Handles text-to-speech synthesis and audio playback
"""
import threading
import queue
import numpy as np
import sounddevice as sd
from pathlib import Path
from typing import Optional, Callable, Dict
from dataclasses import dataclass
from enum import Enum
import sys
import os

# Try to import pocket-tts (must be installed via pip install -e models/pocket-tts)
try:
    from pocket_tts.models.tts_model import TTSModel
    POCKET_TTS_AVAILABLE = True
except ImportError:
    POCKET_TTS_AVAILABLE = False
    print("Warning: pocket-tts not available. Using mock mode.")


class AudioPriority(Enum):
    """Priority levels for audio playback"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AudioRequest:
    """
    Represents an audio playback request
    """
    text: str
    priority: AudioPriority
    callback: Optional[Callable[[], None]] = None


class TTSEngine:
    """
    Text-to-Speech engine with audio queue management
    Handles synthesis and playback with priority-based queue
    """

    # Available voices from pocket-tts
    AVAILABLE_VOICES = [
        "alba", "marius", "javert", "jean", "fantine",
        "cosette", "eponine", "azelma"
    ]

    def __init__(
        self,
        model_path: str = "",
        voice: str = "alba",
        device: Optional[int] = None
    ):
        """
        Initialize the TTS engine

        Args:
            model_path: Path to TTS model directory (not used for pocket-tts)
            voice: Voice to use for synthesis
            device: Audio device ID (None for default)
        """
        self.model_path = Path(model_path)
        self.voice = voice
        self.device = device
        self.tts_model = None
        self.voice_state = None
        self.sample_rate = 24000  # Default, will be updated from model
        self.is_loaded = False
        self.use_pocket_tts = POCKET_TTS_AVAILABLE

        # Audio queue management
        self.audio_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.current_priority = AudioPriority.LOW
        self.is_playing = False
        self.stop_current_playback = False
        self._queue_counter = 0  # Tiebreaker for items with same priority

        # Worker thread
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = False

    def load_model(self) -> bool:
        """
        Load the TTS model

        Returns:
            True if loaded successfully, False otherwise
        """
        if self.use_pocket_tts:
            try:
                print("Loading pocket-tts model...")
                self.tts_model = TTSModel.load_model()
                self.sample_rate = self.tts_model.sample_rate
                self.voice_state = self.tts_model.get_state_for_audio_prompt(self.voice)
                self.is_loaded = True
                print(f"pocket-tts loaded successfully! Voice: {self.voice}, Sample Rate: {self.sample_rate}")
                return True
            except Exception as e:
                print(f"Error loading pocket-tts: {e}. Falling back to mock mode.")
                self.use_pocket_tts = False

        # Fallback to mock mode
        self.is_loaded = True
        print("TTS Engine initialized (mock mode)")
        return True

    def speak(self, text: str, priority: AudioPriority = AudioPriority.NORMAL) -> None:
        """
        Add text to speech queue

        Args:
            text: Text to speak
            priority: Priority level for this speech
        """
        # For urgent messages, clear lower priority items from queue
        if priority == AudioPriority.URGENT:
            self._clear_queue_below(priority)
            # Stop current playback if lower priority
            if self.current_priority.value < priority.value:
                self.stop_current_playback = True

        # Add to queue (use negative priority since PriorityQueue is min-heap)
        # Counter ensures FIFO ordering for items with same priority
        request = AudioRequest(text=text, priority=priority)
        self.audio_queue.put((-priority.value, self._queue_counter, request))
        self._queue_counter += 1

        # Start worker if not running
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._start_worker()

    def speak_sync(self, text: str) -> None:
        """
        Speak text immediately (blocking)

        Args:
            text: Text to speak
        """
        audio_data = self._synthesize(text)
        if audio_data is not None:
            self._play_audio(audio_data)

    def _clear_queue_below(self, priority: AudioPriority) -> None:
        """
        Clear all items in queue below the given priority

        Args:
            priority: Minimum priority to keep
        """
        new_queue = queue.PriorityQueue()

        while not self.audio_queue.empty():
            try:
                item = self.audio_queue.get_nowait()
                _, _, request = item  # Unpack (priority, counter, request)
                if request.priority >= priority:
                    new_queue.put(item)
            except queue.Empty:
                break

        self.audio_queue = new_queue

    def _synthesize(self, text: str) -> Optional[np.ndarray]:
        """
        Synthesize speech from text

        Args:
            text: Text to synthesize

        Returns:
            Audio data as numpy array
        """
        if not self.is_loaded:
            return None

        if self.use_pocket_tts and self.tts_model is not None:
            try:
                # Use pocket-tts for synthesis
                import torch
                audio_tensor = self.tts_model.generate_audio(self.voice_state, text)
                # Convert torch tensor to numpy array
                audio_array = audio_tensor.cpu().numpy()
                # Normalize to float32 for sounddevice
                if audio_array.dtype == np.int16 or audio_array.dtype == np.int32:
                    audio_array = audio_array.astype(np.float32) / np.iinfo(audio_array.dtype).max
                return audio_array.astype(np.float32)
            except Exception as e:
                print(f"Error in pocket-tts synthesis: {e}. Falling back to mock.")

        # Mock implementation - generate a simple tone
        duration = len(text) * 0.08  # Approximate duration
        samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, samples, False)

        # Generate a pleasant tone (sine wave with harmonics)
        frequency = 440  # A4
        audio = (
            0.3 * np.sin(2 * np.pi * frequency * t) +
            0.1 * np.sin(2 * np.pi * frequency * 2 * t) +
            0.05 * np.sin(2 * np.pi * frequency * 3 * t)
        )

        # Apply simple envelope
        envelope = np.ones_like(audio)
        attack = int(0.01 * self.sample_rate)
        release = int(0.1 * self.sample_rate)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[-release:] = np.linspace(1, 0, release)

        audio = audio * envelope

        # Convert to float32 for sounddevice
        return audio.astype(np.float32)

    def _play_audio(self, audio_data: np.ndarray) -> None:
        """
        Play audio data

        Args:
            audio_data: Audio data as numpy array
        """
        try:
            sd.play(audio_data, samplerate=self.sample_rate, device=self.device)
            sd.wait()  # Wait for playback to complete
        except Exception as e:
            print(f"Audio playback error: {e}")

    def _start_worker(self) -> None:
        """Start the audio playback worker thread"""
        self._stop_worker = False
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _stop_worker_thread(self) -> None:
        """Stop the worker thread"""
        self._stop_worker = True
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
            self._worker_thread = None

    def _worker_loop(self) -> None:
        """Worker thread loop for processing audio queue"""
        while not self._stop_worker:
            try:
                # Get request from queue
                try:
                    priority_val, counter, request = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Check if we should stop
                if self._stop_worker:
                    break

                # Set current priority
                self.current_priority = request.priority
                self.is_playing = True

                # Synthesize and play
                audio_data = self._synthesize(request.text)
                if audio_data is not None:
                    self._play_audio(audio_data)

                self.is_playing = False
                self.stop_current_playback = False

                # Call callback if provided
                if request.callback:
                    try:
                        request.callback()
                    except Exception as e:
                        print(f"Callback error: {e}")

            except Exception as e:
                print(f"Worker thread error: {e}")
                self.is_playing = False

    def stop(self) -> None:
        """Stop current playback and clear queue"""
        self.stop_current_playback = True
        sd.stop()
        # Clear entire queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def set_voice(self, voice: str) -> bool:
        """
        Change the voice for synthesis

        Args:
            voice: Name of the voice to use

        Returns:
            True if voice changed successfully
        """
        if not self.use_pocket_tts or self.tts_model is None:
            return False

        if voice in self.AVAILABLE_VOICES:
            try:
                self.voice = voice
                self.voice_state = self.tts_model.get_state_for_audio_prompt(voice)
                print(f"Voice changed to: {voice}")
                return True
            except Exception as e:
                print(f"Error changing voice: {e}")
                return False
        return False

    def get_available_devices(self) -> list:
        """
        Get list of available audio devices

        Returns:
            List of device information dictionaries
        """
        devices = []
        for i, device in enumerate(sd.query_devices()):
            if device['max_output_channels'] > 0:
                devices.append({
                    'id': i,
                    'name': device['name'],
                    'hostapi': device['hostapi']
                })
        return devices

    def test_audio(self) -> None:
        """Test audio playback"""
        self.speak("Audio test complete. All systems operational.", AudioPriority.NORMAL)

    def __del__(self):
        """Cleanup on deletion"""
        self._stop_worker_thread()


class MockTTSEngine(TTSEngine):
    """
    Mock TTS engine for testing without audio output
    Just prints the text that would be spoken
    """

    def _synthesize(self, text: str) -> Optional[np.ndarray]:
        """Mock synthesis - just print"""
        print(f"[TTS] Would speak: {text}")
        return np.array([])  # Return empty array

    def _play_audio(self, audio_data: np.ndarray) -> None:
        """Skip actual playback in mock mode"""
        pass


def test_tts_engine():
    """Test function for TTS Engine"""
    print("Testing TTS Engine...")
    print("Available audio devices:")

    tts = TTSEngine()
    for device in tts.get_available_devices()[:5]:  # Show first 5
        print(f"  [{device['id']}] {device['name']}")

    print("\nTesting audio playback (you should hear tones)...")
    tts.load_model()
    tts.speak("Testing audio system.", AudioPriority.NORMAL)

    # Wait for playback
    import time
    time.sleep(2)

    print("\nTest complete!")


if __name__ == "__main__":
    test_tts_engine()
