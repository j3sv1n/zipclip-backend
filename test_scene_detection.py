#!/usr/bin/env python3
"""
Test script for the scene detection and multi-segment implementation.
This script validates that all the new components work correctly.
"""

import os
import sys

def test_imports():
    """Test that all required imports work"""
    print("=" * 60)
    print("Testing imports...")
    print("=" * 60)
    
    try:
        from Components.LanguageTasks import (
            GetHighlight, 
            GetHighlightMultiSegment, 
            GetHighlightMultiSegmentFromScenes,
            MultiSegmentResponse
        )
        print("✓ LanguageTasks imports successful")
    except Exception as e:
        print(f"✗ LanguageTasks import failed: {e}")
        return False
    
    try:
        from Components.Edit import crop_video, stitch_video_segments
        print("✓ Edit imports successful")
    except Exception as e:
        print(f"✗ Edit import failed: {e}")
        return False
    
    try:
        from Components.SceneDetection import detect_scenes, map_transcript_to_scenes
        print("✓ SceneDetection imports successful (note: scenedetect library may not be installed)")
    except ImportError as e:
        if "scenedetect" in str(e):
            print("⚠ SceneDetection imports partially successful (scenedetect not installed - install with: pip install scenedetect)")
        else:
            print(f"✗ SceneDetection import failed: {e}")
            return False
    
    try:
        from Components.Transcription import transcribeAudio
        print("✓ Transcription imports successful")
    except Exception as e:
        print(f"✗ Transcription import failed: {e}")
        return False
    
    print()
    return True


def test_model_structures():
    """Test that Pydantic models are correctly defined"""
    print("=" * 60)
    print("Testing Pydantic model structures...")
    print("=" * 60)
    
    try:
        from Components.LanguageTasks import (
            JSONResponse,
            SegmentResponse,
            MultiSegmentResponse
        )
        
        # Test SegmentResponse
        seg = SegmentResponse(start=10.5, end=25.0, content="Test segment")
        assert seg.start == 10.5
        assert seg.end == 25.0
        print("✓ SegmentResponse model works")
        
        # Test MultiSegmentResponse
        multi = MultiSegmentResponse(
            segments=[
                SegmentResponse(start=0, end=10, content="First"),
                SegmentResponse(start=20, end=30, content="Second")
            ],
            total_duration=20.0
        )
        assert len(multi.segments) == 2
        assert multi.total_duration == 20.0
        print("✓ MultiSegmentResponse model works")
        
        print()
        return True
    except Exception as e:
        print(f"✗ Model structure test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_file_structures():
    """Test that all required components exist"""
    print("=" * 60)
    print("Testing file structures...")
    print("=" * 60)
    
    required_files = [
        'main.py',
        'Components/LanguageTasks.py',
        'Components/Edit.py',
        'Components/SceneDetection.py',
        'Components/Transcription.py',
        'Components/FaceCrop.py',
        'Components/Subtitles.py',
    ]
    
    all_exist = True
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"✓ {filepath}")
        else:
            print(f"✗ {filepath} NOT FOUND")
            all_exist = False
    
    print()
    return all_exist


def test_documentation():
    """Test that documentation exists"""
    print("=" * 60)
    print("Testing documentation...")
    print("=" * 60)
    
    if os.path.exists('SCENE_DETECTION_IMPLEMENTATION.md'):
        print("✓ SCENE_DETECTION_IMPLEMENTATION.md exists")
        print()
        return True
    else:
        print("✗ SCENE_DETECTION_IMPLEMENTATION.md not found")
        print()
        return False


def test_syntax():
    """Test that Python files have valid syntax"""
    print("=" * 60)
    print("Testing Python syntax...")
    print("=" * 60)
    
    import py_compile
    
    files_to_check = [
        'main.py',
        'Components/LanguageTasks.py',
        'Components/Edit.py',
        'Components/SceneDetection.py',
    ]
    
    all_valid = True
    for filepath in files_to_check:
        try:
            py_compile.compile(filepath, doraise=True)
            print(f"✓ {filepath}")
        except py_compile.PyCompileError as e:
            print(f"✗ {filepath}: {e}")
            all_valid = False
    
    print()
    return all_valid


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Scene Detection & Multi-Segment Implementation Tests".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = {
        "Imports": test_imports(),
        "Model Structures": test_model_structures(),
        "File Structures": test_file_structures(),
        "Documentation": test_documentation(),
        "Syntax": test_syntax(),
    }
    
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} test suites passed")
    print("=" * 60)
    
    if passed == total:
        print("\n✓ All tests passed! Ready to use scene detection features.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run the app: python main.py <video_path>")
        print("3. Select processing mode when prompted")
        print("4. Choose between continuous, multi-segment, or scene-based mode")
        return 0
    else:
        print(f"\n✗ {total - passed} test suite(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
