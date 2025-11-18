#!/usr/bin/env python3
"""
Quick test script to verify subtitle positioning in generated ASS files.
"""

import sys
sys.path.insert(0, 'src')

from clipsmachine.subtitles import generate_ass_subtitle_file, SubtitleWord
from clipsmachine.subtitle_styles import create_subtitle_style, style_to_ass_format
from clipsmachine.whisper_transcribe import generate_word_by_word_subtitles_ass
import tempfile
import os


def test_keywords_subtitle_positioning():
    """Test subtitle positioning in keywords-based ASS file."""
    print("=" * 60)
    print("Testing Keywords Subtitle Positioning")
    print("=" * 60)

    # Create test subtitle words
    test_words = [
        SubtitleWord(word="BECAUSE", start_time=0.0, end_time=0.5),
        SubtitleWord(word="YOU", start_time=0.5, end_time=0.8),
        SubtitleWord(word="GAVE", start_time=0.8, end_time=1.2),
    ]

    # Generate ASS file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False) as f:
        output_path = f.name

    try:
        generate_ass_subtitle_file(test_words, output_path, video_width=1080, video_height=1920)

        # Read and check the file
        with open(output_path, 'r') as f:
            content = f.read()

        print("\n📄 Generated ASS File Content (Style section):\n")

        # Extract and display style line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('Style: Default'):
                print(f"Line {i}: {line}")

                # Parse the style values
                parts = line.split(',')
                if len(parts) >= 23:
                    alignment = parts[18]
                    margin_v = parts[21]

                    print(f"\n✓ Alignment: {alignment} (expected: 2 for bottom-center)")
                    print(f"✓ MarginV: {margin_v} (expected: 850)")

                    if alignment == '2' and margin_v == '850':
                        print("\n✅ SUCCESS: Keywords subtitles are correctly positioned!")
                        return True
                    else:
                        print("\n❌ FAILED: Incorrect positioning values!")
                        return False

    finally:
        os.remove(output_path)

    return False


def test_transcription_subtitle_positioning():
    """Test subtitle positioning in Whisper transcription-based ASS file."""
    print("\n" + "=" * 60)
    print("Testing Transcription Subtitle Positioning")
    print("=" * 60)

    # Create mock transcript object
    class MockWord:
        def __init__(self, word, start, end):
            self.word = word
            self.start = start
            self.end = end

    class MockTranscript:
        def __init__(self):
            self.words = [
                MockWord("Because", 0.0, 0.5),
                MockWord("you", 0.5, 0.8),
                MockWord("gave", 0.8, 1.2),
            ]

    # Generate ASS file with default style config
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False) as f:
        output_path = f.name

    try:
        transcript = MockTranscript()
        generate_word_by_word_subtitles_ass(
            transcript=transcript,
            output_path=output_path,
            words_per_line=3,
            video_width=1080,
            video_height=1920,
            style_config={}  # Use defaults
        )

        # Read and check the file
        with open(output_path, 'r') as f:
            content = f.read()

        print("\n📄 Generated ASS File Content (Style section):\n")

        # Extract and display style line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('Style: Default'):
                print(f"Line {i}: {line}")

                # Parse the style values
                parts = line.split(',')
                if len(parts) >= 23:
                    alignment = parts[18]
                    margin_v = parts[21]

                    print(f"\n✓ Alignment: {alignment} (expected: 2 for bottom-center)")
                    print(f"✓ MarginV: {margin_v} (expected: 850)")

                    if alignment == '2' and margin_v == '850':
                        print("\n✅ SUCCESS: Transcription subtitles are correctly positioned!")
                        return True
                    else:
                        print("\n❌ FAILED: Incorrect positioning values!")
                        return False

    finally:
        os.remove(output_path)

    return False


def test_subtitle_style_defaults():
    """Test that subtitle_styles.py has correct defaults."""
    print("\n" + "=" * 60)
    print("Testing Subtitle Style Defaults")
    print("=" * 60)

    style = create_subtitle_style()  # Use all defaults

    print(f"\n✓ Default alignment: {style.alignment} (expected: 2)")
    print(f"✓ Default margin_v: {style.margin_v} (expected: 850)")

    if style.alignment == 2 and style.margin_v == 850:
        print("\n✅ SUCCESS: Default style configuration is correct!")
        return True
    else:
        print("\n❌ FAILED: Default style configuration is incorrect!")
        return False


if __name__ == "__main__":
    print("\n🎬 ClipsMachine Subtitle Positioning Test Suite\n")

    results = []

    # Run all tests
    results.append(("Keywords Positioning", test_keywords_subtitle_positioning()))
    results.append(("Transcription Positioning", test_transcription_subtitle_positioning()))
    results.append(("Style Defaults", test_subtitle_style_defaults()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All tests passed! Subtitle positioning is fixed.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        sys.exit(1)
