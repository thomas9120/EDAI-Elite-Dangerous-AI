"""
LLM Engine - The Brain of EDAI
Handles local LLM inference using llama-cpp-python
"""
import threading
import queue
from pathlib import Path
from typing import Optional, Callable
import time


class LLMEngine:
    """
    Local LLM inference engine using llama-cpp-python
    Runs generation in a separate thread to avoid blocking the UI
    """

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 2048,
        n_gpu_layers: int = -1,
        max_tokens: int = 50,
        temperature: float = 0.8,
        system_prompt: str = ""
    ):
        """
        Initialize the LLM engine

        Args:
            model_path: Path to the .gguf model file
            n_ctx: Context window size
            n_gpu_layers: Number of layers to offload to GPU (-1 for all)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: System prompt for the AI personality
        """
        self.model_path = Path(model_path)
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt

        self.llm = None
        self.is_loaded = False
        self.generation_queue: queue.Queue = queue.Queue()
        self.response_callbacks: list = []

        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = False

    def load_model(self) -> bool:
        """
        Load the LLM model into memory

        Returns:
            True if model loaded successfully, False otherwise
        """
        if not self.model_path.exists():
            print(f"Model file not found: {self.model_path}")
            return False

        try:
            from llama_cpp import Llama

            print(f"Loading model: {self.model_path}")
            print(f"Context: {self.n_ctx}, GPU Layers: {self.n_gpu_layers}")

            self.llm = Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False
            )

            self.is_loaded = True
            print("Model loaded successfully!")
            return True

        except ImportError:
            print("ERROR: llama-cpp-python not installed. Run: pip install llama-cpp-python")
            return False
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def unload_model(self) -> None:
        """Unload the model from memory"""
        self.llm = None
        self.is_loaded = False

    def set_system_prompt(self, prompt: str) -> None:
        """
        Update the system prompt

        Args:
            prompt: New system prompt
        """
        self.system_prompt = prompt

    def generate(self, event_text: str, callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Generate a response to an event (non-blocking)

        Args:
            event_text: Formatted event description
            callback: Optional callback function for the response
        """
        if callback:
            self.response_callbacks.append(callback)

        # Add to generation queue
        self.generation_queue.put(event_text)

        # Start worker thread if not running
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._start_worker()

    def generate_sync(self, event_text: str) -> str:
        """
        Generate a response to an event (blocking)

        Args:
            event_text: Formatted event description

        Returns:
            Generated response text
        """
        if not self.is_loaded or self.llm is None:
            return "Model not loaded."

        prompt = self._build_prompt(event_text)

        try:
            response = self.llm(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=["\n", "Commander:", "AI:", "User:"],
                echo=False
            )

            # Extract generated text
            generated = response["choices"][0]["text"].strip()
            return self._clean_response(generated)

        except Exception as e:
            print(f"Generation error: {e}")
            return "I'm having trouble processing that, Commander."

    def _build_prompt(self, event_text: str) -> str:
        """
        Build the full prompt for the LLM

        Args:
            event_text: Formatted event description

        Returns:
            Full prompt string
        """
        # Template for Gemma 2 Instruct
        prompt = f"""<start_of_turn>user
{self.system_prompt}

Event: {event_text}

Provide a brief, in-character response (under 20 words).<end_of_turn>
<start_of_turn>model
"""
        return prompt

    def _clean_response(self, response: str) -> str:
        """
        Clean up the LLM response

        Args:
            response: Raw response from LLM

        Returns:
            Cleaned response string
        """
        # Remove common artifacts
        response = response.strip()

        # Remove quotes if the entire response is quoted
        if len(response) >= 2 and response[0] in '"\'"' and response[-1] == response[0]:
            response = response[1:-1]

        # Remove common prefixes
        for prefix in ["Response:", "AI:", "Model:", "Orca:", "Ship:"]:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()

        return response

    def _start_worker(self) -> None:
        """Start the background worker thread"""
        self._stop_worker = False
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _stop_worker_thread(self) -> None:
        """Stop the background worker thread"""
        self._stop_worker = True
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
            self._worker_thread = None

    def _worker_loop(self) -> None:
        """Worker thread loop for processing generation queue"""
        while not self._stop_worker:
            try:
                # Get event from queue with timeout
                try:
                    event_text = self.generation_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Generate response
                response = self.generate_sync(event_text)

                # Call callbacks
                for callback in self.response_callbacks:
                    try:
                        callback(response)
                    except Exception as e:
                        print(f"Callback error: {e}")

                # Clear callbacks
                self.response_callbacks.clear()

            except Exception as e:
                print(f"Worker thread error: {e}")

    def test_generation(self) -> str:
        """
        Test the LLM with a sample prompt

        Returns:
            Generated response
        """
        test_event = "FSD Jump complete. Arrived at Shinrarta Dezhra."
        return self.generate_sync(test_event)

    def __del__(self):
        """Cleanup on deletion"""
        self._stop_worker_thread()


class MockLLMEngine(LLMEngine):
    """
    Mock LLM engine for testing without a real model
    Returns predefined responses based on event type
    """

    MOCK_RESPONSES = {
        "FSDJump": "Jump complete. Welcome to {system}, Commander.",
        "DockingGranted": "Docking permission confirmed. Approach with caution.",
        "DockingDenied": "They refused us docking permission. Rude.",
        "ShieldState": "Shields are down. I hope you know what you're doing.",
        "ShipLowFuel": "We're running on fumes here! Find a fuel scoop!",
        "Bounty": "Another bounty collected. That's more credits for us.",
        "Died": "Systems... failing... Commander...",
        "MaterialCollected": "Material acquired. Adding to inventory.",
        "Scan": "Scan complete. Data logged.",
        "Undocked": "Released from station. Free to roam.",
        "SupercruiseEntry": "Engaging supercruise drive.",
        "SupercruiseExit": "Dropping to normal space.",
        "FuelFull": "Tanks topped off. Ready to go.",
        "StartJump": "Spooling frame shift drive.",
        "LoadGame": "Systems online. Welcome back, Commander.",
    }

    def load_model(self) -> bool:
        """Mock model loading - always returns True"""
        self.is_loaded = True
        print("Mock LLM loaded")
        return True

    def generate_sync(self, event_text: str) -> str:
        """Generate a mock response"""
        # Try to find the event type in the text
        for event_type, response_template in self.MOCK_RESPONSES.items():
            if event_type in event_text:
                return response_template

        # Default response
        return "Acknowledged, Commander."


def test_llm_engine():
    """Test function for LLM Engine"""
    import os

    # Mock test (doesn't require real model)
    print("Testing Mock LLM Engine...")
    mock_llm = MockLLMEngine(
        model_path="dummy.gguf",
        system_prompt="You are a sarcastic ship AI."
    )
    mock_llm.load_model()

    # Test generation
    test_events = [
        "FSD Jump complete. Arrived at Shinrarta Dezhra.",
        "Docking granted at Jameson Memorial."
    ]

    for event in test_events:
        print(f"\nEvent: {event}")
        response = mock_llm.generate_sync(event)
        print(f"Response: {response}")

    print("\nTo test with a real model, ensure you have:")
    print("1. llama-cpp-python installed")
    print("2. A .gguf model file in the models folder")


if __name__ == "__main__":
    test_llm_engine()
