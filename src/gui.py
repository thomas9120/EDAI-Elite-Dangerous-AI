"""
GUI - Main User Interface for EDAI
Built with CustomTkinter for a modern dark theme
"""
import customtkinter as ctk
from tkinter import filedialog, scrolledtext, messagebox
import threading
import queue
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from config import Config
from journal_watcher import JournalWatcher
from event_parser import EventParser, ParsedEvent
from llm_engine import LLMEngine, MockLLMEngine
from tts_engine import TTSEngine, MockTTSEngine, AudioPriority
from game_state import get_game_state_tracker


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EDAIApp(ctk.CTk):
    """
    Main EDAI Application GUI
    """

    def __init__(self):
        super().__init__()

        # Configuration
        self.config = Config()

        # Window setup
        self.title("EDAI - Elite Dangerous AI Interface")
        self.geometry("900x700")
        self.minsize(800, 600)

        # Use dark theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Application state
        self.is_running = False
        self.watcher: Optional[JournalWatcher] = None
        self.parser: Optional[EventParser] = None
        self.llm: Optional[LLMEngine] = None
        self.tts: Optional[TTSEngine] = None
        self.game_state = get_game_state_tracker()

        # Queue for thread-safe GUI updates
        self.event_queue = queue.Queue()

        # Build UI
        self._build_ui()

        # Start update checker
        self._check_queue()

    def _build_ui(self):
        """Build the main user interface"""
        # Main container with padding
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="EDAI - Elite Dangerous AI Interface",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        # Status Frame
        self._build_status_frame(main_frame)

        # Content Frame (paned window for resizeable areas)
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill="both", expand=True, pady=(10, 10))

        # Left panel - Events
        left_panel = ctk.CTkFrame(content_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))

        event_label = ctk.CTkLabel(
            left_panel,
            text="Recent Events",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        event_label.pack(pady=(10, 5))

        self.event_text = scrolledtext.ScrolledText(
            left_panel,
            wrap="word",
            height=15,
            font=("Consolas", 10)
        )
        self.event_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Right panel - AI Responses
        right_panel = ctk.CTkFrame(content_frame)
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))

        response_label = ctk.CTkLabel(
            right_panel,
            text="AI Responses",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        response_label.pack(pady=(10, 5))

        self.response_text = scrolledtext.ScrolledText(
            right_panel,
            wrap="word",
            height=15,
            font=("Consolas", 10)
        )
        self.response_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Control Frame
        self._build_control_frame(main_frame)

    def _build_status_frame(self, parent):
        """Build the status indicator frame"""
        status_frame = ctk.CTkFrame(parent, height=60)
        status_frame.pack(fill="x", pady=(0, 10))
        status_frame.pack_propagate(False)

        # Status indicator
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="● STOPPED",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="gray"
        )
        self.status_label.pack(side="left", padx=20)

        # Journal info
        self.journal_label = ctk.CTkLabel(
            status_frame,
            text=f"Journal: {self.config.journal_path}",
            font=ctk.CTkFont(size=12)
        )
        self.journal_label.pack(side="left", padx=20)

        # Model status
        self.model_label = ctk.CTkLabel(
            status_frame,
            text="Model: Not Loaded",
            font=ctk.CTkFont(size=12)
        )
        self.model_label.pack(side="right", padx=20)

    def _build_control_frame(self, parent):
        """Build the control button frame"""
        control_frame = ctk.CTkFrame(parent, height=80)
        control_frame.pack(fill="x", pady=(10, 0))
        control_frame.pack_propagate(False)

        # Start/Stop button
        self.start_button = ctk.CTkButton(
            control_frame,
            text="Start Monitoring",
            command=self.toggle_monitoring,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="green",
            hover_color="darkgreen",
            width=150
        )
        self.start_button.pack(side="left", padx=20)

        # Test Audio button
        test_button = ctk.CTkButton(
            control_frame,
            text="Test Audio",
            command=self.test_audio,
            font=ctk.CTkFont(size=14),
            width=120
        )
        test_button.pack(side="left", padx=10)

        # Chat button
        chat_button = ctk.CTkButton(
            control_frame,
            text="Chat",
            command=self.open_chat,
            font=ctk.CTkFont(size=14),
            width=120
        )
        chat_button.pack(side="left", padx=10)

        # Settings button
        settings_button = ctk.CTkButton(
            control_frame,
            text="Settings",
            command=self.open_settings,
            font=ctk.CTkFont(size=14),
            width=120
        )
        settings_button.pack(side="right", padx=20)

        # Clear button
        clear_button = ctk.CTkButton(
            control_frame,
            text="Clear Logs",
            command=self.clear_logs,
            font=ctk.CTkFont(size=14),
            width=120
        )
        clear_button.pack(side="right", padx=10)

    def _check_queue(self):
        """Check for updates from worker threads"""
        try:
            while not self.event_queue.empty():
                event_type, data = self.event_queue.get_nowait()
                if event_type == "event":
                    self._add_event_log(data)
                elif event_type == "response":
                    self._add_response_log(data)
                elif event_type == "status":
                    self._update_status(data)
        except queue.Empty:
            pass

        # Schedule next check
        self.after(100, self._check_queue)

    def _add_event_log(self, text: str):
        """Add an event to the event log"""
        self.event_text.insert("end", text + "\n")
        self.event_text.see("end")

    def _add_response_log(self, text: str):
        """Add an AI response to the response log"""
        self.response_text.insert("end", text + "\n")
        self.response_text.see("end")

    def _update_status(self, status: str):
        """Update the status label"""
        if status == "running":
            self.status_label.configure(text="● RUNNING", text_color="#00FF00")
        elif status == "stopped":
            self.status_label.configure(text="● STOPPED", text_color="gray")
        elif status == "error":
            self.status_label.configure(text="● ERROR", text_color="red")

    def toggle_monitoring(self):
        """Toggle monitoring on/off"""
        if self.is_running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        """Start monitoring the journal file"""
        logger.info("Starting monitoring...")

        # Initialize parser
        self.parser = EventParser(
            whitelist=set(self.config.events_whitelist),
            urgent_events=set(self.config.urgent_events)
        )

        # Initialize LLM
        use_mock = not Path(self.config.llm_model_path).exists()
        if use_mock:
            logger.warning("LLM model not found, using mock")
            self.llm = MockLLMEngine(
                model_path=self.config.llm_model_path,
                system_prompt=self.config.system_prompt
            )
        else:
            self.llm = LLMEngine(
                model_path=self.config.llm_model_path,
                n_ctx=self.config.n_ctx,
                n_gpu_layers=self.config.n_gpu_layers,
                max_tokens=self.config.max_tokens,
                system_prompt=self.config.system_prompt
            )

        if not self.llm.load_model():
            messagebox.showerror("Error", "Failed to load LLM model")
            return

        # Initialize TTS
        self.tts = TTSEngine(
            model_path=self.config.tts_model_path,
            voice=self.config.voice_selection
        )
        self.tts.load_model()

        # Initialize watcher
        def on_event(event_data: Dict):
            self._handle_event(event_data)

        self.watcher = JournalWatcher(self.config.journal_path, on_event)

        if not self.watcher.start():
            messagebox.showerror(
                "Error",
                f"Failed to start journal watcher.\n\n"
                f"Check that the journal path is correct:\n"
                f"{self.config.journal_path}"
            )
            return

        # Update UI
        self.is_running = True
        self.start_button.configure(
            text="Stop Monitoring",
            fg_color="red",
            hover_color="darkred"
        )
        self._update_status("running")
        self.model_label.configure(text="Model: Loaded")

        logger.info("Monitoring started")

    def stop_monitoring(self):
        """Stop monitoring"""
        logger.info("Stopping monitoring...")

        if self.watcher:
            self.watcher.stop()
            self.watcher = None

        if self.tts:
            self.tts.stop()
            self.tts = None

        if self.llm:
            self.llm.unload_model()
            self.llm = None

        self.parser = None

        # Update UI
        self.is_running = False
        self.start_button.configure(
            text="Start Monitoring",
            fg_color="green",
            hover_color="darkgreen"
        )
        self._update_status("stopped")
        self.model_label.configure(text="Model: Not Loaded")

        logger.info("Monitoring stopped")

    def _handle_event(self, event_data: Dict):
        """Handle a journal event"""
        if not self.parser:
            return

        # Update game state (always do this, even for initial state loading)
        self.game_state.update(event_data)

        # Debug: Log game state updates
        event_name = event_data.get("event", "")
        if event_name in ["LoadGame", "FSDJump", "Docked", "Undocked", "ShipRefuelled", "ShieldState", "ShipLowFuel"]:
            print(f"[GAME STATE UPDATE] {event_name}: Current system={self.game_state.state.current_system}, Fuel={self.game_state.state.fuel_level}/{self.game_state.state.fuel_capacity}, Shields={'UP' if self.game_state.state.shields_up else 'DOWN'}")

        # Handle special InitialStateLoaded event
        if event_name == "InitialStateLoaded":
            self._announce_initial_state()
            return

        # Check if this is part of initial state loading (don't speak these)
        if event_data.get("_initial_state_loading", False):
            # Still log to event log, but don't speak
            parsed = self.parser.parse(event_data)
            if parsed:
                timestamp = event_data.get("timestamp", "")
                self.event_queue.put(("event", f"[{timestamp}] {parsed.formatted_text} (state loaded)"))
            return

        # Parse event
        parsed = self.parser.parse(event_data)
        if not parsed:
            return

        # Add to event log
        timestamp = event_data.get("timestamp", "")
        self.event_queue.put(("event", f"[{timestamp}] {parsed.formatted_text}"))

        # Check for urgent event (use canned response)
        if parsed.is_urgent:
            from event_parser import get_canned_response
            canned = get_canned_response(parsed.event_type)
            if canned:
                self.event_queue.put(("response", f"[URGENT] {canned}"))
                self.tts.speak(canned, AudioPriority.URGENT)
                return

        # Check if raw data mode is enabled
        if self.config.raw_data_mode:
            # Speak the formatted text directly without LLM
            print(f"[RAW DATA MODE] Speaking: {parsed.formatted_text}")
            self.event_queue.put(("response", f"[{parsed.event_type}] {parsed.formatted_text}"))
            if self.tts:
                self.tts.speak(parsed.formatted_text, AudioPriority.NORMAL)
            return

        # Generate LLM response
        if self.llm:
            def on_response(response: str):
                print(f"[EVENT] {parsed.event_type} → LLM Response: {response}")
                self.event_queue.put(("response", f"[{parsed.event_type}] {response}"))
                if self.tts:
                    self.tts.speak(response, AudioPriority.NORMAL)

            # Add prefix to help LLM understand this is a system update, not user chat
            event_with_prefix = f"Ship's computer status update: {parsed.formatted_text}"
            print(f"[EVENT] Sending to LLM: {event_with_prefix}")
            self.llm.generate(event_with_prefix, on_response)

    def _announce_initial_state(self):
        """Announce a summary of the current game state after initial load"""
        state_desc = self.game_state.state.get_context_description()

        if not state_desc or state_desc == "No game state available yet.":
            return

        print(f"[INITIAL STATE] Summary: {state_desc}")

        # Add to response log
        self.event_queue.put(("response", f"[STATE LOADED] {state_desc}"))

        # Speak the summary
        if self.tts and not self.config.raw_data_mode:
            # Generate a friendly announcement
            announcement_prompt = f"Summarize this game state in one brief sentence: {state_desc}"

            def on_response(response: str):
                print(f"[INITIAL STATE] Announcement: {response}")
                self.tts.speak(response, AudioPriority.NORMAL)

            self.llm.generate(announcement_prompt, on_response)
        elif self.tts:
            # In raw data mode, just speak the state directly
            self.tts.speak(state_desc, AudioPriority.NORMAL)

    def test_audio(self):
        """Test the audio system"""
        if not self.tts:
            messagebox.showwarning("Warning", "Start monitoring first to initialize audio")
            return

        self.tts.test_audio()
        self.event_queue.put(("response", "[TEST] Audio test complete."))

    def clear_logs(self):
        """Clear the log displays"""
        self.event_text.delete("1.0", "end")
        self.response_text.delete("1.0", "end")

    def open_settings(self):
        """Open the settings window"""
        SettingsWindow(self, self.config)

    def open_chat(self):
        """Open the chat window"""
        ChatWindow(self)


class SettingsWindow(ctk.CTkToplevel):
    """Settings configuration window"""

    def __init__(self, parent: EDAIApp, config: Config):
        super().__init__(parent)

        self.parent = parent
        self.config = config

        self.title("Settings")
        self.geometry("700x600")
        self.minsize(600, 500)

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        """Build the settings UI"""
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Tabbed interface
        self.tabview = ctk.CTkTabview(main_frame, width=650, height=450)
        self.tabview.pack(fill="both", expand=True)

        # Create tabs
        self.tabview.add("General")
        self.tabview.add("Events")

        # Build each tab
        self._build_general_tab(self.tabview.tab("General"))
        self._build_events_tab(self.tabview.tab("Events"))

        # Buttons (outside tabs)
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self.save_settings,
            fg_color="green",
            hover_color="darkgreen",
            width=100
        )
        save_button.pack(side="right", padx=10)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=100
        )
        cancel_button.pack(side="right", padx=10)

    def _build_general_tab(self, parent):
        """Build the General settings tab"""
        # Scrollable frame for content
        container = ctk.CTkScrollableFrame(parent)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Journal Path
        self._add_path_setting(
            container,
            "Journal Path",
            "journal_path",
            "Folder containing Elite Dangerous Journal files"
        )

        # LLM Model Path
        self._add_path_setting(
            container,
            "LLM Model Path",
            "llm_model_path",
            "Path to the .gguf model file"
        )

        # TTS Model Path
        self._add_path_setting(
            container,
            "TTS Model Path",
            "tts_model_path",
            "Path to TTS model directory"
        )

        # Voice Selection
        voice_frame = ctk.CTkFrame(container)
        voice_frame.pack(fill="x", pady=(10, 20))

        voice_label = ctk.CTkLabel(
            voice_frame,
            text="TTS Voice",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        voice_label.pack(anchor="w", pady=(10, 5))

        from tts_engine import TTSEngine
        self.voice_dropdown = ctk.CTkOptionMenu(
            voice_frame,
            values=TTSEngine.AVAILABLE_VOICES,
            command=self._on_voice_change
        )
        self.voice_dropdown.pack(fill="x", padx=10, pady=(0, 10))

        # System Prompt
        prompt_frame = ctk.CTkFrame(container)
        prompt_frame.pack(fill="x", pady=(10, 20))

        prompt_label = ctk.CTkLabel(
            prompt_frame,
            text="System Prompt (AI Personality)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        prompt_label.pack(anchor="w", pady=(10, 5))

        self.system_prompt_text = ctk.CTkTextbox(prompt_frame, height=120)
        self.system_prompt_text.pack(fill="x", padx=10, pady=(0, 10))

        # Max Tokens
        tokens_frame = ctk.CTkFrame(container)
        tokens_frame.pack(fill="x", pady=(10, 20))

        tokens_label = ctk.CTkLabel(
            tokens_frame,
            text="Max Response Tokens",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        tokens_label.pack(anchor="w", pady=(10, 5))

        self.max_tokens_entry = ctk.CTkEntry(tokens_frame)
        self.max_tokens_entry.pack(fill="x", padx=10, pady=(0, 10))

        # Raw Data Mode
        raw_frame = ctk.CTkFrame(container)
        raw_frame.pack(fill="x", pady=(10, 20))

        self.raw_data_var = ctk.BooleanVar()
        self.raw_data_checkbox = ctk.CTkCheckBox(
            raw_frame,
            text="Raw Data Mode (speak event data directly, bypass LLM)",
            variable=self.raw_data_var,
            checkbox_width=20,
            font=ctk.CTkFont(size=12)
        )
        self.raw_data_checkbox.pack(anchor="w", padx=10, pady=(10, 5))
        raw_info = ctk.CTkLabel(
            raw_frame,
            text="When enabled, the ship AI will read event data directly without AI interpretation.\nUseful for accurate information or testing.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        raw_info.pack(anchor="w", padx=30, pady=(0, 10))

    def _build_events_tab(self, parent):
        """Build the Events selection tab"""
        from event_metadata import EVENT_DISPLAY_NAMES, ALL_AVAILABLE_EVENTS

        # Main container with padding
        container = ctk.CTkFrame(parent)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Header with description
        header_frame = ctk.CTkFrame(container)
        header_frame.pack(fill="x", pady=(0, 10))

        header_label = ctk.CTkLabel(
            header_frame,
            text="Select which events should trigger AI responses:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header_label.pack(anchor="w", padx=10, pady=10)

        # Scrollable frame for event checkboxes
        events_scroll = ctk.CTkScrollableFrame(container, height=350)
        events_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Quick action buttons
        button_frame = ctk.CTkFrame(container)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))

        select_all_btn = ctk.CTkButton(
            button_frame,
            text="Select All",
            command=self._select_all_events,
            width=100
        )
        select_all_btn.pack(side="left", padx=5)

        select_none_btn = ctk.CTkButton(
            button_frame,
            text="Select None",
            command=self._select_none_events,
            width=100
        )
        select_none_btn.pack(side="left", padx=5)

        # Event checkboxes
        self.event_checkboxes = {}
        for event_name in ALL_AVAILABLE_EVENTS:
            display_name = EVENT_DISPLAY_NAMES.get(event_name, event_name)
            var = ctk.BooleanVar()
            checkbox = ctk.CTkCheckBox(
                events_scroll,
                text=display_name,
                variable=var,
                font=ctk.CTkFont(size=12)
            )
            checkbox.pack(anchor="w", padx=10, pady=2)
            self.event_checkboxes[event_name] = var

    def _select_all_events(self):
        """Select all event checkboxes"""
        for var in self.event_checkboxes.values():
            var.set(True)

    def _select_none_events(self):
        """Deselect all event checkboxes"""
        for var in self.event_checkboxes.values():
            var.set(False)

    def _add_path_setting(self, parent: ctk.CTkScrollableFrame, label: str, key: str, tooltip: str):
        """Add a path setting row"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=(10, 0))

        label_widget = ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label_widget.pack(anchor="w", padx=10, pady=(10, 5))

        # Container for entry + browse button
        entry_container = ctk.CTkFrame(frame, fg_color="transparent")
        entry_container.pack(fill="x", padx=10, pady=(0, 10))

        entry = ctk.CTkEntry(entry_container)
        entry.pack(side="left", fill="x", expand=True)

        def browse():
            path = filedialog.askdirectory()
            if path:
                entry.delete(0, "end")
                entry.insert(0, path)

        browse_btn = ctk.CTkButton(
            entry_container,
            text="Browse...",
            command=browse,
            width=80
        )
        browse_btn.pack(side="right", padx=(10, 0))

        # Store reference
        setattr(self, f"{key}_entry", entry)

    def _load_settings(self):
        """Load settings into UI"""
        # General settings
        self.journal_path_entry.insert("0", self.config.journal_path)
        self.llm_model_path_entry.insert("0", str(self.config.llm_model_path))
        self.tts_model_path_entry.insert("0", str(self.config.tts_model_path))
        self.voice_dropdown.set(self.config.voice_selection)
        self.system_prompt_text.insert("1.0", self.config.system_prompt)
        self.max_tokens_entry.insert("0", str(self.config.max_tokens))

        # Raw Data Mode checkbox
        self.raw_data_var.set(self.config.raw_data_mode)

        # Event checkboxes
        current_whitelist = set(self.config.events_whitelist)
        for event_name, var in self.event_checkboxes.items():
            var.set(event_name in current_whitelist)

    def _on_voice_change(self, choice: str):
        """Handle voice selection change"""
        pass  # Voice is saved when settings are saved

    def save_settings(self):
        """Save settings from UI"""
        # General settings
        self.config.set("journal_path", self.journal_path_entry.get())
        self.config.set("llm_model_path", self.llm_model_path_entry.get())
        self.config.set("tts_model_path", self.tts_model_path_entry.get())
        self.config.set("voice_selection", self.voice_dropdown.get())
        self.config.set("system_prompt", self.system_prompt_text.get("1.0", "end").strip())

        try:
            self.config.set("max_tokens", int(self.max_tokens_entry.get()))
        except ValueError:
            messagebox.showerror("Error", "Max tokens must be a number")
            return

        # Raw Data Mode
        self.config.set("raw_data_mode", self.raw_data_var.get())

        # Event whitelist
        selected_events = [event for event, var in self.event_checkboxes.items() if var.get()]

        # Warn if no events selected
        if not selected_events:
            result = messagebox.askyesno(
                "No Events Selected",
                "You haven't selected any events. The AI will not respond to anything.\n\n"
                "Are you sure you want to save?"
            )
            if not result:
                return

        self.config.set("events_whitelist", selected_events)

        if self.config.save():
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to save settings")


class ChatWindow(ctk.CTkToplevel):
    """Chat window for talking to the AI"""

    def __init__(self, parent: EDAIApp):
        super().__init__(parent)

        self.parent = parent

        self.title("EDAI - Chat with AI")
        self.geometry("700x600")
        self.minsize(600, 500)

        self._build_ui()

    def _build_ui(self):
        """Build the chat UI"""
        # Main container with padding
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Chat with Ship AI",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 10))

        # Chat history (scrollable text area)
        self.chat_history = scrolledtext.ScrolledText(
            main_frame,
            wrap="word",
            height=20,
            font=("Consolas", 11),
            state="normal"
        )
        self.chat_history.pack(fill="both", expand=True, pady=(0, 10))

        # Add welcome message
        self._add_message("System", "AI communication channel open. Type your message below and press Enter or click Send.", "gray")

        # Input frame
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x")

        # Text input
        self.chat_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type a message to the AI...",
            height=40
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)
        self.chat_entry.bind("<Return>", lambda e: self.send_message())
        self.chat_entry.focus_set()

        # Send button
        send_button = ctk.CTkButton(
            input_frame,
            text="Send",
            command=self.send_message,
            width=100,
            height=40,
            fg_color="blue",
            hover_color="darkblue"
        )
        send_button.pack(side="right", padx=10, pady=10)

    def _add_message(self, sender: str, text: str, color: str = None):
        """Add a message to the chat history"""
        self.chat_history.insert("end", f"[{sender}]: ", ("bold",))
        self.chat_history.insert("end", f"{text}\n")
        if color:
            # Apply color to the last line
            end_index = self.chat_history.index("end-1c linestart")
            self.chat_history.tag_add(color, end_index, "end")
            self.chat_history.tag_config(color, foreground=color)
        self.chat_history.see("end")

    def send_message(self):
        """Send a message to the AI"""
        message = self.chat_entry.get().strip()
        if not message:
            return

        # Clear the entry
        self.chat_entry.delete("0", "end")

        # Check if monitoring is running
        if not self.parent.is_running or not self.parent.llm:
            self._add_message("System", "Please start monitoring first to use the chat function.", "red")
            return

        # Add user message to history
        self._add_message("You", message)

        # Check if raw data mode is enabled
        if self.parent.config.raw_data_mode:
            # Just speak the game state directly without LLM
            context = self.parent.game_state.get_chat_context(message)
            self._add_message("System", f"Raw Data: {context}", "#8888ff")
            if self.parent.tts:
                self.parent.tts.speak(context, AudioPriority.NORMAL)
            return

        # Get game state context
        context = self.parent.game_state.get_chat_context(message)

        # Generate enhanced prompt with context
        enhanced_prompt = f"""CURRENT GAME STATE:
{context}

IMPORTANT: You must ONLY use the information provided above in "CURRENT GAME STATE". If the information is not available there, say you don't know. Do NOT make up system names, locations, or any other information.

Commander's message: {message}"""

        # Debug: Log what's being sent to LLM
        print("=" * 80)
        print("[CHAT] Sending to LLM:")
        print("-" * 80)
        print(enhanced_prompt)
        print("-" * 80)
        print("=" * 80)

        # Also add to chat history for visibility
        self._add_message("Debug", f"Context: {self.parent.game_state.state.current_system or 'Unknown'}", "#888888")

        # Generate response
        def on_response(response: str):
            print(f"[CHAT] LLM Response: {response}")
            self._add_message("AI", response, "#00FF00")
            if self.parent.tts:
                self.parent.tts.speak(response, AudioPriority.NORMAL)

        self.parent.llm.generate(enhanced_prompt, on_response)


def main():
    """Main entry point"""
    app = EDAIApp()
    app.mainloop()


if __name__ == "__main__":
    main()
