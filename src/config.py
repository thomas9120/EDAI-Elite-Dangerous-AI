"""
Configuration Management for EDAI
Handles loading and saving of settings
"""
import json
import os
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration manager for EDAI"""

    DEFAULT_CONFIG: Dict[str, Any] = {
        "journal_path": os.path.expanduser("~\\Saved Games\\Frontier Developments\\Elite Dangerous"),
        "llm_model_path": "models\\gemma-2-2b-it-abliterated.Q4_K_M.gguf",
        "tts_model_path": "models\\pocket-tts",
        "system_prompt": "You are the AI of an Elite Dangerous ship called the 'Orca'. You are sarcastic but helpful. Keep responses under 20 words. Stay in character as a ship's computer.",
        "voice_selection": "alba",
        "n_ctx": 4096,
        "n_gpu_layers": -1,
        "max_tokens": 50,
        "temperature": 0.3,
        "audio_device": None,
        "events_whitelist": [
            "FSDJump", "DockingGranted", "ShieldState", "ShipLowFuel",
            "Bounty", "Died", "MaterialCollected", "DockingDenied",
            "JumpReq", "FuelFull", "Scan", "SAASignalsFound"
        ],
        "urgent_events": ["ShipLowFuel", "Died", "ShieldState"]
    }

    def __init__(self, config_path: str = None):
        """
        Initialize configuration manager

        Args:
            config_path: Path to settings.json file
        """
        if config_path is None:
            # Get the directory of this file
            current_dir = Path(__file__).parent
            config_path = current_dir.parent / "settings" / "settings.json"

        self.config_path = Path(config_path)
        self.settings: Dict[str, Any] = {}

        # Create config directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create config
        self.load()

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file

        Returns:
            The loaded settings dictionary
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
                self.settings = self.DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self.settings = self.DEFAULT_CONFIG.copy()
            self.save()

        return self.settings

    def save(self) -> bool:
        """
        Save current configuration to file

        Returns:
            True if save was successful, False otherwise
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            The configuration value or default
        """
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value

        Args:
            key: Configuration key
            value: Value to set
        """
        self.settings[key] = value

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update multiple configuration values

        Args:
            updates: Dictionary of key-value pairs to update
        """
        self.settings.update(updates)

    @property
    def journal_path(self) -> str:
        """Get the journal path with environment variables expanded"""
        path = self.get("journal_path", "")
        return os.path.expandvars(path)

    @property
    def llm_model_path(self) -> str:
        """Get the LLM model path"""
        return str(Path(self.get("llm_model_path", "")))

    @property
    def tts_model_path(self) -> str:
        """Get the TTS model path"""
        return str(Path(self.get("tts_model_path", "")))

    @property
    def system_prompt(self) -> str:
        """Get the system prompt"""
        return self.get("system_prompt", self.DEFAULT_CONFIG["system_prompt"])

    @property
    def voice_selection(self) -> str:
        """Get the selected TTS voice"""
        return self.get("voice_selection", "alba")

    @property
    def n_ctx(self) -> int:
        """Get context window size for LLM"""
        return self.get("n_ctx", 2048)

    @property
    def n_gpu_layers(self) -> int:
        """Get number of GPU layers for LLM"""
        return self.get("n_gpu_layers", -1)

    @property
    def temperature(self) -> float:
        """Get temperature for LLM generation"""
        return self.get("temperature", 0.8)

    @property
    def max_tokens(self) -> int:
        """Get max tokens for LLM generation"""
        return self.get("max_tokens", 50)

    @property
    def events_whitelist(self) -> list:
        """Get list of events to process"""
        return self.get("events_whitelist", self.DEFAULT_CONFIG["events_whitelist"])

    @property
    def urgent_events(self) -> list:
        """Get list of urgent events that bypass normal queue"""
        return self.get("urgent_events", self.DEFAULT_CONFIG["urgent_events"])
