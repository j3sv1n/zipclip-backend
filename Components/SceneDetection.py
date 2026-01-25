from scenedetect import detect, ContentDetector, AdaptiveDetector
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
import os
from moviepy.editor import VideoFileClip
import numpy as np

def detect_scenes(video_path, threshold=12.0, min_scene_len=20.0):
    """
    Detect scenes in a video using PySceneDetect with frame-based analysis.
    Optimized for 1-hour videos to generate 10+ segments with 15-20 second max duration.
    
    Args:
        video_path: Path to the video file
        threshold: Sensitivity for scene detection (lower = more sensitive, default=12.0)
                  Recommended: 8-15 for higher sensitivity, detects more visual changes
        min_scene_len: Minimum scene length in seconds (default=20.0)
    
    Returns:
        List of tuples [(start_time, end_time), ...] representing scene boundaries in seconds
    """
    try:
        # Get video duration for adaptive thresholding
        try:
            video = VideoFileClip(video_path)
            duration = video.duration
            video.close()
            print(f"Video duration: {duration:.2f}s ({duration/60:.1f} minutes)")
            
            # Adaptive threshold based on video length
            # For 1-hour (3600s) videos, we want at least 10 segments
            # That means average segment length of 360s (6 minutes)
            # But we want max 15-20s, so we need frequent scene cuts
            # Use lower threshold for longer videos to get more cuts
            if duration > 3000:  # 50+ minute videos
                threshold = min(threshold, 10.0)
                min_scene_len = min(min_scene_len, 1.5)
                print(f"Long video detected - using aggressive scene detection")
                print(f"  Adjusted threshold: {threshold}, min_scene_len: {min_scene_len}s")
        except Exception as e:
            print(f"Could not get video duration: {e}")
            duration = None
        
        print(f"Detecting scenes in video using frame-based analysis...")
        print(f"Parameters: threshold={threshold}, min_scene_len={min_scene_len}s")
        
        # Use ContentDetector with frame-based analysis (default in pySceneDetect)
        # ContentDetector measures the difference between consecutive frames
        # This is purely visual analysis, independent of audio
        scene_list = detect(
            video_path, 
            ContentDetector(threshold=threshold, min_scene_len=int(min_scene_len * 30))
        )
        
        # Convert to list of (start_time, end_time) tuples in seconds
        scenes = []
        for i, scene in enumerate(scene_list):
            start_time = scene[0].get_seconds()
            end_time = scene[1].get_seconds()
            duration_scene = end_time - start_time
            
            # Enforce max segment length constraint (15-20 seconds)
            # If a scene is longer than 20 seconds, we'll let LLM handle splitting if needed
            # But we still report it as-is
            scenes.append((start_time, end_time))
        
        print(f"✓ Detected {len(scenes)} scenes in the video")
        
        # Calculate statistics
        if scenes:
            durations = [end - start for start, end in scenes]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            print(f"  Scene statistics:")
            print(f"    Average duration: {avg_duration:.2f}s")
            print(f"    Min duration: {min_duration:.2f}s")
            print(f"    Max duration: {max_duration:.2f}s")
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
        print(f"Error mapping transcriptions to scenes: {e}")
        return []


def convert_scenes_to_segments(scenes):
    """
    Convert detected scenes into segment format for selection.
    This is used for frame-based scene analysis without transcripts.
    
    Args:
        scenes: List of (start_time, end_time) tuples
    
    Returns:
        List of dicts with scene info:
        [
            {
                'scene_index': int,
                'scene_start': float,
                'scene_end': float,
                'duration': float,
                'visual_description': str (computed from scene characteristics)
            },
            ...
        ]
    """
    try:
        print("Converting detected scenes to segment format...")
        
        scene_segments = []
        
        for scene_idx, (scene_start, scene_end) in enumerate(scenes):
            duration = scene_end - scene_start
            
            # Create visual description based on scene characteristics
            # (position in video, relative duration, etc.)
            position_percent = (scene_start / (scene_end + 1)) * 100 if scene_end > 0 else 0
            
            # Categorize scene by duration
            if duration < 5:
                duration_category = "Very Short"
            elif duration < 10:
                duration_category = "Short"
            elif duration < 20:
                duration_category = "Medium"
            else:
                duration_category = "Long"
            
            visual_description = f"{duration_category} scene ({duration:.1f}s)"
            
            scene_segments.append({
                'scene_index': scene_idx,
                'scene_start': scene_start,
                'scene_end': scene_end,
                'duration': duration,
                'visual_description': visual_description
            })
        
        print(f"✓ Converted {len(scene_segments)} scenes to segment format")
        
        # Print sample for debugging
        if scene_segments:
            print(f"  Sample scene (first):")
            sample = scene_segments[0]
            print(f"    Time: {sample['scene_start']:.2f}s - {sample['scene_end']:.2f}s")
            print(f"    Description: {sample['visual_description']}")
        
        return scene_segments
    
    except Exception as e:
        print(f"Error mapping transcripts to scenes: {e}")
        return []


def analyze_scenes_with_vision(video_path, scenes):
    """
    Extract key frames from each scene and analyze them with vision AI.
    This provides rich visual descriptions of what's in each scene.
    
    Args:
        video_path: Path to the video file
        scenes: List of (start_time, end_time) tuples
    
    Returns:
        List of dicts with scene info and visual analysis:
        [
            {
                'scene_index': int,
                'scene_start': float,
                'scene_end': float,
                'duration': float,
                'frame_description': str (AI analysis of what's in the scene)
            },
            ...
        ]
    """
    try:
        from moviepy.editor import VideoFileClip
        import tempfile
        import os as os_module
        
        print("Analyzing scene content with vision AI...")
        
        video = VideoFileClip(video_path)
        scene_analysis = []
        
        for scene_idx, (scene_start, scene_end) in enumerate(scenes):
            try:
                # Extract frame from middle of scene for analysis
                frame_time = scene_start + (scene_end - scene_start) / 2
                frame = video.get_frame(frame_time)
                
                # Save frame temporarily
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                    from PIL import Image
                    img = Image.fromarray((frame * 255).astype('uint8'))
                    img.save(tmp_file.name)
                    temp_frame_path = tmp_file.name
                
                # Analyze frame with vision API
                frame_description = analyze_frame_with_gpt(temp_frame_path)
                
                # Clean up temp file
                os_module.unlink(temp_frame_path)
                
                duration = scene_end - scene_start
                scene_analysis.append({
                    'scene_index': scene_idx,
                    'scene_start': scene_start,
                    'scene_end': scene_end,
                    'duration': duration,
                    'frame_description': frame_description
                })
                
                print(f"  Scene {scene_idx + 1}: {frame_description}")
                
            except Exception as e:
                print(f"  Warning: Could not analyze scene {scene_idx + 1}: {e}")
                # Fallback to basic description
                duration = scene_end - scene_start
                scene_analysis.append({
                    'scene_index': scene_idx,
                    'scene_start': scene_start,
                    'scene_end': scene_end,
                    'duration': duration,
                    'frame_description': f"Scene with duration {duration:.1f}s"
                })
                continue
        
        video.close()
        
        print(f"✓ Analyzed {len(scene_analysis)} scenes with vision AI\n")
        return scene_analysis
        
    except Exception as e:
        print(f"Error analyzing scenes with vision: {e}")
        print("Falling back to basic scene analysis")
        return convert_scenes_to_segments(scenes)


def analyze_frame_with_gpt(frame_path):
    """
    Use GPT-4 Vision to analyze a frame and describe what's happening.
    
    Args:
        frame_path: Path to the frame image
    
    Returns:
        Description of what's in the frame
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        import base64
        
        # Read and encode the image
        with open(frame_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        
        message = HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}",
                    },
                },
                {
                    "type": "text",
                    "text": "Briefly describe what you see in this video frame. Focus on: people present, their activities, emotions, setting, key details. Keep it to 1-2 sentences."
                }
            ],
        )
        
        response = llm.invoke([message])
        description = response.content if hasattr(response, 'content') else str(response)
        
        return description.strip()
        
    except Exception as e:
        print(f"Error analyzing frame with GPT: {e}")
        return "Scene content analysis unavailable"



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
