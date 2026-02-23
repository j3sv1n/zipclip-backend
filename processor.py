"""
Video Processor Wrapper
Wraps the main video processing logic for API usage without modifying core functionality.
"""

from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video, stitch_video_segments
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight, GetHighlightMultiSegment, GetHighlightMultiSegmentFromFrames
from Components.SceneDetection import detect_scenes, analyze_scenes_with_vision
from Components.FaceCrop import crop_to_vertical, combine_videos
from Components.Subtitles import add_subtitles_to_video
import os
import uuid
import re
from typing import Callable, Optional, Dict, List, Tuple


def clean_filename(title: str) -> str:
    """Clean and slugify title for filename."""
    cleaned = title.lower()
    cleaned = re.sub(r'[<>:"/\\|?*\[\]]', '', cleaned)
    cleaned = re.sub(r'[\s_]+', '-', cleaned)
    cleaned = re.sub(r'-+', '-', cleaned)
    cleaned = cleaned.strip('-')
    return cleaned[:80]


def process_video(
    video_url_or_path: str,
    mode: str = 'continuous',
    add_subtitles: bool = True,
    target_duration: int = 120,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    session_id: Optional[str] = None
) -> Dict[str, any]:
    """
    Process a video to create a short clip.
    
    Args:
        video_url_or_path: YouTube URL or local file path
        mode: Processing mode ('continuous', 'multi_segment', 'scene_based')
        add_subtitles: Whether to add subtitles
        target_duration: Target duration in seconds
        progress_callback: Callback function(message, progress_percent)
        session_id: Unique session identifier
    
    Returns:
        Dict with 'success', 'output_file', 'error' keys
    """
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]
    
    # Helper function to update progress
    def update_progress(message: str, percent: int):
        if progress_callback:
            progress_callback(message, percent)
    
    try:
        # Create output directories
        output_dir = "output_videos"
        audio_dir = "audio"
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)
        
        update_progress("Starting video processing...", 5)
        
        # Download or load video
        video_title = None
        if os.path.isfile(video_url_or_path):
            update_progress("Loading local video file...", 10)
            Vid = video_url_or_path
            video_title = os.path.splitext(os.path.basename(video_url_or_path))[0]
        else:
            update_progress("Downloading from YouTube...", 10)
            Vid = download_youtube_video(video_url_or_path)
            if Vid:
                Vid = Vid.replace(".webm", ".mp4")
                video_title = os.path.splitext(os.path.basename(Vid))[0]
            else:
                return {"success": False, "error": "Failed to download video"}
        
        update_progress("Extracting audio...", 20)
        
        # Create unique temporary filenames
        audio_file = os.path.join(audio_dir, f"audio_{session_id}.wav")
        temp_clip = f"temp_clip_{session_id}.mp4"
        temp_cropped = f"temp_cropped_{session_id}.mp4"
        temp_subtitled = f"temp_subtitled_{session_id}.mp4"
        temp_stitched = f"temp_stitched_{session_id}.mp4"
        
        Audio = extractAudio(Vid, audio_file)
        if not Audio:
            return {"success": False, "error": "Failed to extract audio"}
        
        update_progress("Transcribing audio...", 30)
        transcriptions = transcribeAudio(Audio)
        
        if len(transcriptions) == 0:
            return {"success": False, "error": "No transcriptions found"}
        
        update_progress("Analyzing transcription...", 50)
        
        # Build transcription text
        TransText = ""
        for segment in transcriptions:
            TransText += f"{segment['start']} - {segment['end']}: {segment['text']}\n"
        
        # Process based on mode
        segments = None
        
        if mode == 'continuous':
            update_progress("Finding best continuous highlight...", 55)
            start, stop = GetHighlight(TransText)
            
            if start is None or stop is None:
                return {"success": False, "error": "Failed to get highlight from LLM"}
            
            segments = [{'start': start, 'end': stop}]
        
        elif mode == 'multi_segment':
            update_progress("Finding multiple important segments...", 55)
            segments = GetHighlightMultiSegment(TransText, target_duration=target_duration)
            
            if segments is None:
                return {"success": False, "error": "Failed to get segments from LLM"}
        
        elif mode == 'scene_based':
            update_progress("Detecting scenes...", 55)
            scenes = detect_scenes(Vid)
            
            if not scenes:
                return {"success": False, "error": "Failed to detect scenes"}
            
            update_progress("Analyzing scene content...", 60)
            scene_segments = analyze_scenes_with_vision(Vid, scenes)
            
            if not scene_segments:
                return {"success": False, "error": "Failed to analyze scenes"}
            
            update_progress("Selecting important scenes...", 65)
            segments = GetHighlightMultiSegmentFromFrames(scene_segments, target_duration=target_duration)
            
            if segments is None:
                return {"success": False, "error": "Failed to select scenes from LLM"}
        
        if not segments or len(segments) == 0:
            return {"success": False, "error": "No segments selected"}
        
        update_progress(f"Processing {len(segments)} segment(s)...", 70)
        
        # Generate final output filename
        clean_title = clean_filename(video_title) if video_title else "output"
        final_output = os.path.join(output_dir, f"{clean_title}_{session_id}_zipped.mp4")
        
        if len(segments) == 1:
            update_progress("Extracting single segment...", 75)
            seg = segments[0]
            crop_video(Vid, temp_clip, seg['start'], seg['end'])
        else:
            update_progress(f"Stitching {len(segments)} segments...", 75)
            if not stitch_video_segments(Vid, segments, temp_stitched):
                return {"success": False, "error": "Failed to stitch video segments"}
            temp_clip = temp_stitched
        
        update_progress("Cropping to vertical format...", 80)
        crop_to_vertical(temp_clip, temp_cropped)
        
        if add_subtitles:
            update_progress("Adding subtitles...", 85)
            # Pass all segments for correct timing mapping
            add_subtitles_to_video(
                temp_cropped, 
                temp_subtitled, 
                transcriptions, 
                segments=segments,
                subtitle_offset=0.0 # Can be made configurable if needed
            )
            
            update_progress("Adding audio to final video...", 90)
            combine_videos(temp_clip, temp_subtitled, final_output)
        else:
            update_progress("Adding audio to final video...", 90)
            combine_videos(temp_clip, temp_cropped, final_output)
        
        update_progress("Cleaning up temporary files...", 95)
        
        # Clean up temporary files
        temp_files = [audio_file, temp_clip, temp_cropped, temp_subtitled, temp_stitched]
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"Warning: Could not remove {temp_file}: {e}")
        
        update_progress("Processing complete!", 100)
        
        return {
            "success": True,
            "output_file": final_output,
            "segments": segments,
            "video_title": video_title
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
