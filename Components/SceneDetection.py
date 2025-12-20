from scenedetect import detect, ContentDetector, AdaptiveDetector
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
import os

def detect_scenes(video_path, threshold=27.0, min_scene_len=3.0):
    """
    Detect scenes in a video using PySceneDetect.
    
    Args:
        video_path: Path to the video file
        threshold: Sensitivity for scene detection (lower = more sensitive, default=27.0)
        min_scene_len: Minimum scene length in seconds (default=3.0)
    
    Returns:
        List of tuples [(start_time, end_time), ...] representing scene boundaries in seconds
    """
    try:
        print(f"Detecting scenes in video... (threshold={threshold}, min_scene_len={min_scene_len}s)")
        
        # Use the simple detect API
        scene_list = detect(video_path, ContentDetector(threshold=threshold, min_scene_len=int(min_scene_len * 30)))
        
        # Convert to list of (start_time, end_time) tuples in seconds
        scenes = []
        for i, scene in enumerate(scene_list):
            start_time = scene[0].get_seconds()
            end_time = scene[1].get_seconds()
            scenes.append((start_time, end_time))
        
        print(f"✓ Detected {len(scenes)} scenes in the video")
        
        # Print first few scenes for debugging
        if scenes:
            print(f"  First 5 scenes:")
            for i, (start, end) in enumerate(scenes[:5]):
                print(f"    Scene {i+1}: {start:.2f}s - {end:.2f}s ({end-start:.2f}s)")
        
        return scenes
    
    except Exception as e:
        print(f"Error detecting scenes: {e}")
        print(f"Falling back to simple time-based segmentation")
        # Fallback: create 10-second segments
        from moviepy.editor import VideoFileClip
        try:
            video = VideoFileClip(video_path)
            duration = video.duration
            video.close()
            
            scenes = []
            segment_length = 10.0
            current = 0
            while current < duration:
                end = min(current + segment_length, duration)
                scenes.append((current, end))
                current = end
            
            print(f"✓ Created {len(scenes)} time-based segments (fallback)")
            return scenes
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")
            return []


def map_transcript_to_scenes(scenes, transcriptions):
    """
    Map transcription segments to detected scenes.
    
    Args:
        scenes: List of (start_time, end_time) tuples for each scene
        transcriptions: List of [text, start, end] from Whisper transcription
    
    Returns:
        List of dicts with scene info and associated transcripts:
        [
            {
                'scene_start': float,
                'scene_end': float,
                'duration': float,
                'transcript': str (concatenated text for this scene)
            },
            ...
        ]
    """
    try:
        print("Mapping transcriptions to scenes...")
        
        scene_transcripts = []
        
        for scene_idx, (scene_start, scene_end) in enumerate(scenes):
            # Find all transcription segments that overlap with this scene
            scene_text_parts = []
            
            for text, trans_start, trans_end in transcriptions:
                # Check if transcription segment overlaps with scene
                # Overlap occurs if: trans_start < scene_end AND trans_end > scene_start
                if trans_start < scene_end and trans_end > scene_start:
                    scene_text_parts.append(text.strip())
            
            # Combine all text for this scene
            combined_text = " ".join(scene_text_parts)
            
            scene_transcripts.append({
                'scene_index': scene_idx,
                'scene_start': scene_start,
                'scene_end': scene_end,
                'duration': scene_end - scene_start,
                'transcript': combined_text
            })
        
        print(f"✓ Mapped {len(scene_transcripts)} scenes with transcripts")
        
        # Print sample for debugging
        if scene_transcripts:
            print(f"  Sample scene (first):")
            sample = scene_transcripts[0]
            print(f"    Time: {sample['scene_start']:.2f}s - {sample['scene_end']:.2f}s")
            print(f"    Text preview: {sample['transcript'][:100]}...")
        
        return scene_transcripts
    
    except Exception as e:
        print(f"Error mapping transcripts to scenes: {e}")
        return []


def create_scene_summary_for_llm(scene_transcripts):
    """
    Create a formatted summary of scenes with transcripts for LLM analysis.
    
    Args:
        scene_transcripts: List of scene dicts from map_transcript_to_scenes
    
    Returns:
        Formatted string with scene information
    """
    summary_parts = []
    summary_parts.append("SCENES WITH TRANSCRIPTS:\n")
    summary_parts.append("=" * 80 + "\n")
    
    for scene in scene_transcripts:
        summary_parts.append(
            f"Scene {scene['scene_index'] + 1}: "
            f"{scene['scene_start']:.2f}s - {scene['scene_end']:.2f}s "
            f"(duration: {scene['duration']:.2f}s)\n"
        )
        summary_parts.append(f"Text: {scene['transcript']}\n")
        summary_parts.append("-" * 80 + "\n")
    
    return "".join(summary_parts)


if __name__ == "__main__":
    # Test the scene detection
    test_video = "test_video.mp4"
    if os.path.exists(test_video):
        scenes = detect_scenes(test_video)
        print(f"\nDetected {len(scenes)} scenes")
        for i, (start, end) in enumerate(scenes[:10]):  # Show first 10
            print(f"Scene {i+1}: {start:.2f}s - {end:.2f}s ({end-start:.2f}s)")
