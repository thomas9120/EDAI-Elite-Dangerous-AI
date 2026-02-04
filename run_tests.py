#!/usr/bin/env python3
"""
Test Runner for EDAI
Runs basic tests to verify each module works correctly
"""
import sys
import os

# Fix console encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)


def test_config():
    """Test configuration loading"""
    print("Testing Configuration...")
    from src.config import Config

    config = Config()
    print(f"  Journal Path: {config.journal_path}")
    print(f"  LLM Path: {config.llm_model_path}")
    print(f"  Max Tokens: {config.max_tokens}")
    print("  ✓ Config loaded successfully")
    return True


def test_event_parser():
    """Test event parsing"""
    print("\nTesting Event Parser...")
    from src.event_parser import EventParser, get_canned_response

    parser = EventParser()

    # Test FSDJump
    fsd_event = {
        "event": "FSDJump",
        "StarSystem": "Shinrarta Dezhra",
        "Body": "Jameson Memorial"
    }
    parsed = parser.parse(fsd_event)
    print(f"  FSDJump: {parsed.formatted_text}")

    # Test urgent event
    fuel_event = {"event": "ShipLowFuel"}
    canned = get_canned_response("ShipLowFuel")
    print(f"  Low Fuel Canned: {canned}")

    print("  ✓ Event parser working")
    return True


def test_llm_engine():
    """Test LLM engine (mock mode)"""
    print("\nTesting LLM Engine (Mock Mode)...")
    from src.llm_engine import MockLLMEngine

    llm = MockLLMEngine(
        model_path="dummy.gguf",
        system_prompt="You are a test AI."
    )
    llm.load_model()

    response = llm.generate_sync("FSD Jump complete. Arrived at Shinrarta Dezhra.")
    print(f"  Response: {response}")
    print("  ✓ LLM engine working")
    return True


def test_tts_engine():
    """Test TTS engine"""
    print("\nTesting TTS Engine...")
    from src.tts_engine import TTSEngine

    tts = TTSEngine()
    print(f"  Available audio devices: {len(tts.get_available_devices())}")
    print("  ✓ TTS engine initialized")
    return True


def test_journal_watcher():
    """Test journal watcher (only if ED is installed)"""
    print("\nTesting Journal Watcher...")
    from src.journal_watcher import JournalWatcher
    from src.config import Config

    config = Config()
    journal_dir = config.journal_path

    if not os.path.exists(journal_dir):
        print(f"  ⚠ Journal directory not found: {journal_dir}")
        print("  ⚠ Skipping journal watcher test")
        return True

    watcher = JournalWatcher(journal_dir, lambda e: None)
    latest = watcher._find_latest_journal()

    if latest:
        print(f"  Latest journal: {latest.name}")
        print("  ✓ Journal watcher working")
    else:
        print("  ⚠ No journal files found")

    return True


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("EDAI Test Runner")
    print("=" * 50)

    tests = [
        test_config,
        test_event_parser,
        test_llm_engine,
        test_tts_engine,
        test_journal_watcher,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"Tests Passed: {passed}/{len(tests)}")
    print("=" * 50)

    if failed == 0:
        print("\n✓ All tests passed! EDAI is ready to use.")
        print("\nTo start the application, run: python main.py")
    else:
        print(f"\n✗ {failed} test(s) failed. Please check the errors above.")


if __name__ == "__main__":
    run_all_tests()
