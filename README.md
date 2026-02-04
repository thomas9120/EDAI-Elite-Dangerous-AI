# EDAI - Elite Dangerous AI Interface

A local AI companion for Elite Dangerous that monitors game logs and provides vocal, in-character responses using local LLM and TTS models.

## Features

- **Journal Watching**: Monitors Elite Dangerous game logs in real-time
- **Event Filtering**: Intelligently filters relevant game events
- **AI Responses**: Uses a local LLM to generate contextual, in-character responses
- **Text-to-Speech**: Converts AI responses to audio using local TTS
- **Priority Audio Queue**: Urgent events (shield down, low fuel) get immediate attention
- **Modern GUI**: Built with CustomTkinter for a sleek dark theme

## Requirements

- Python 3.10+
- Windows OS
- Elite Dangerous installed

## Installation

### 1. Clone or Download

```bash
cd "Project Fish"
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download Models

#### LLM Model (Optional - Mock mode works without it)
Download a Gemma 2 2B model in GGUF format for intelligent responses:
- Model: `ZeroWw/gemma-2-2b-it-abliterated-SILLY`
- Format: `.gguf` (Q4_K_M or Q5_K_M quantization recommended)
- Place in: `models/` folder
- The app will use mock responses if the model is not found

#### TTS Engine (Optional - Mock mode works without it)
pocket-tts is already included in the `models/pocket-tts` folder. To enable it:

1. **Install PyTorch** (CPU version is sufficient):
   ```bash
   pip install torch>=2.5.0 torchaudio>=2.5.0
   ```

2. **Install pocket-tts from the local folder**:
   ```bash
   cd models/pocket-tts
   pip install -e .
   ```

   Or install from PyPI:
   ```bash
   pip install pocket-tts
   ```

**Available Voices:**
- `alba` (default, female)
- `marius` (male)
- `javert` (male)
- `jean` (male)
- `fantine` (female)
- `cosette` (female)
- `eponine` (female)
- `azelma` (female)

You can change the voice in the settings or use a custom voice file for voice cloning.

## Usage

### Running the Application

```bash
python main.py
```

### Configuration

On first run, configure the settings:

1. **Journal Path**: Your Elite Dangerous saved games folder
   - Default: `%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous`

2. **Model Paths**: Point to where you installed the models

3. **System Prompt**: Customize your AI's personality

### Controls

- **Start/Stop Monitoring**: Toggle journal watching
- **Test Audio**: Verify TTS output
- **Settings**: Configure paths and prompts

## Project Structure

```
Project Fish/
├── main.py              # Entry point
├── requirements.txt     # Python dependencies
├── settings/
│   └── settings.json    # Default configuration
├── src/
│   ├── __init__.py
│   ├── config.py        # Configuration management
│   ├── journal_watcher.py  # Journal file monitoring
│   ├── event_parser.py     # Event filtering and formatting
│   ├── llm_engine.py       # LLM inference
│   ├── tts_engine.py       # Text-to-speech
│   └── gui.py              # Main GUI
└── models/               # Place model files here
```

## How It Works

1. **Journal Watcher** monitors Elite Dangerous log files for new events
2. **Event Parser** filters relevant events and formats them for the AI
3. **LLM Engine** generates contextual responses based on the system prompt
4. **TTS Engine** converts responses to speech and plays them

## Event Types

The AI responds to events including:
- FSD Jump
- Docking Granted/Denied
- Shield State changes
- Low Fuel warnings
- Bounty collection
- Material collection
- And more...

## Troubleshooting

### "Failed to start journal watcher"
- Verify Elite Dangerous is installed
- Check the journal path in Settings

### "Model not found"
- Ensure the `.gguf` file is in the `models/` folder
- Verify the model path in Settings

### No audio output
- Check your system audio settings
- Use "Test Audio" button to verify

## Development

### Running Tests

Test individual modules:

```bash
# Test journal watcher
python -m src.journal_watcher

# Test LLM engine
python -m src.llm_engine

# Test TTS engine
python -m src.tts_engine
```

## Building an Executable

Using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

## License

This project is provided as-is for educational and personal use.

## Acknowledgments

- Elite Dangerous by Frontier Developments
- llama.cpp for GGUF model support
- Gemma 2 by Google
- Kyutai for pocket-tts
- CustomTkinter for the GUI framework
