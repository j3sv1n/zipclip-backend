"""
Video Processor Wrapper
Wraps the main video processing logic for API usage without modifying core functionality.
"""

from moviepy.editor import VideoFileClip, ImageClip
from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video, stitch_video_segments, apply_background_music
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight, GetHighlightMultiSegment, GetHighlightMultiSegmentFromFrames, GetCoherentHighlights, GetMusicMood
from Components.SceneDetection import detect_scenes, analyze_scenes_with_vision, analyze_frame_with_gpt
from Components.FaceCrop import crop_to_vertical, combine_videos
from Components.Subtitles import add_subtitles_to_video
from Components.Music import select_and_download_music
import os
import tempfile
import uuid
import re
from typing import Callable, Optional, Dict, List, Tuple
from PIL import Image


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


def process_multi_media(
    file_paths: List[str],
    add_subtitles: bool = True,
    target_duration: int = 60,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    session_id: Optional[str] = None,
    mode: str = 'continuous'
) -> Dict[str, any]:
    """
    Process multiple media files (images/videos) to create a coherent short clip.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]
    
    def update_progress(message: str, percent: int):
        if progress_callback:
            progress_callback(message, percent)
    
    try:
        output_dir = "output_videos"
        audio_dir = "audio"
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)
        
        # Generate final output filename
        final_output = os.path.join(output_dir, f"coherent_{session_id}_zipped.mp4")
        
        update_progress("Analyzing multiple media files...", 10)
        
        # Sort files sequentially by filename so users can dictate the order
        file_paths = sorted(file_paths, key=lambda x: os.path.basename(x))
        
        media_metadata = []
        temp_clips = [] # Keep track of video clips generated from images
        
        for i, path in enumerate(file_paths):
            update_progress(f"Processing file {i+1}/{len(file_paths)}: {os.path.basename(path)}", 10 + int(i * 30 / len(file_paths)))
            
            ext = os.path.splitext(path)[1].lower()
            is_image = ext in ['.jpg', '.jpeg', '.png', '.webp']
            
            if is_image:
                item = {
                    'index': len(media_metadata),
                    'filename': os.path.basename(path),
                    'path': path,
                    'type': 'image',
                    'visual_description': analyze_frame_with_gpt(path),
                    'duration': 5.0,
                    'transcript': "",
                    'file_index': i
                }
                media_metadata.append(item)
            else:
                # Video: Transcribe + Quick visual analysis
                # Extract audio first
                audio_file = os.path.join(audio_dir, f"audio_{session_id}_{i}.wav")
                Audio = extractAudio(path, audio_file)
                transcriptions = []
                if Audio:
                    transcriptions = transcribeAudio(Audio)
                    if os.path.exists(audio_file): os.remove(audio_file)
                
                trans_text = " ".join([seg['text'] for seg in transcriptions])
                
                if mode == 'scene_based':
                    from Components.SceneDetection import detect_scenes, analyze_scenes_with_vision
                    scenes = detect_scenes(path)
                    if not scenes:
                        from moviepy.editor import VideoFileClip
                        with VideoFileClip(path) as v:
                            scenes = [(0.0, v.duration)]
                    scene_segments = analyze_scenes_with_vision(path, scenes)
                    
                    for s in scene_segments:
                        item = {
                            'index': len(media_metadata),
                            'filename': os.path.basename(path),
                            'path': path,
                            'type': 'video',
                            'duration': s['duration'],
                            'visual_description': s.get('frame_description', ''),
                            'transcript': trans_text, # passing full video transcript is fine for LLM context
                            'transcriptions_full': transcriptions,
                            'scene_start': s['scene_start'],
                            'scene_end': s['scene_end'],
                            'file_index': i
                        }
                        media_metadata.append(item)
                else:
                    with VideoFileClip(path) as v:
                        duration = v.duration
                        # Analyze first and middle frames
                        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                            v.save_frame(tmp.name, t=min(1.0, duration/2))
                            v_desc = analyze_frame_with_gpt(tmp.name)
                            os.unlink(tmp.name)
                    item = {
                        'index': len(media_metadata),
                        'filename': os.path.basename(path),
                        'path': path,
                        'type': 'video',
                        'duration': duration,
                        'visual_description': v_desc,
                        'transcript': trans_text,
                        'transcriptions_full': transcriptions,
                        'file_index': i
                    }
                    media_metadata.append(item)
        
        update_progress("Finding coherent connections between files...", 50)
        highlights_result = GetCoherentHighlights(media_metadata, target_duration=target_duration)
        
        if not highlights_result or 'segments' not in highlights_result:
            return {"success": False, "error": "Failed to find coherent segments"}
            
        selected_segments = highlights_result['segments']
        theme = highlights_result.get('theme', 'A coherent and engaging short video')
        
        update_progress(f"Generating clips for {len(selected_segments)} segments...", 60)
        
        final_segments = []
        all_transcriptions = []
        current_offset = 0.0
        
        for i, seg in enumerate(selected_segments):
            m_idx = seg['media_index']
            media = media_metadata[m_idx]
            
            seg_path = media['path']
            if media['type'] == 'image':
                # Bypass intermediate file writing for images, use direct clip
                from moviepy.editor import ImageClip
                ic = ImageClip(media['path']).set_duration(5.0)
                seg['clip'] = ic
                seg['start'] = 0.0
                seg['end'] = 5.0
                seg_path = media['path']
            else:
                if 'scene_start' in media:
                    # Map relative segment times within the scene to absolute video times
                    seg_start_offset = seg['start']
                    seg_end_offset = seg['end']
                    seg['start'] = media['scene_start'] + seg_start_offset
                    seg['end'] = min(media['scene_start'] + seg_end_offset, media['scene_end'])
            
            seg['file_path'] = seg_path
            final_segments.append(seg)
            
            # If it's a video segment, add its transcriptions with offset
            if media['type'] == 'video' and 'transcriptions_full' in media:
                for t_seg in media['transcriptions_full']:
                    # Only add transcriptions that fall within the segment range
                    if t_seg['start'] >= seg['start'] and t_seg['end'] <= seg['end']:
                        all_transcriptions.append({
                            'text': t_seg['text'],
                            'start': t_seg['start'] - seg['start'] + current_offset,
                            'end': t_seg['end'] - seg['start'] + current_offset
                        })
            current_offset += (seg['end'] - seg['start'])

        temp_stitched = f"temp_stitched_{session_id}.mp4"
        temp_cropped = f"temp_cropped_{session_id}.mp4"
        temp_subtitled = f"temp_subtitled_{session_id}.mp4"
        temp_with_music = f"temp_music_{session_id}.mp4"
        
        update_progress("Stitching all segments together...", 80)
        # Using None for input_file since segments have file_path
        if not stitch_video_segments(None, final_segments, temp_stitched, theme=theme):
            return {"success": False, "error": "Failed to stitch segments"}
        
        update_progress("Finalizing video format...", 85)
        crop_to_vertical(temp_stitched, temp_cropped)
        
        update_progress("Selecting background music...", 90)
        mood = GetMusicMood(theme, media_metadata)
        music_file = select_and_download_music(mood)
        
        if music_file:
            update_progress("Applying background music with ducking...", 92)
            if apply_background_music(temp_cropped, music_file, all_transcriptions, temp_with_music):
                ready_video = temp_with_music
            else:
                ready_video = temp_cropped
        else:
            ready_video = temp_cropped
            
        if add_subtitles and all_transcriptions:
            update_progress("Adding subtitles...", 97)
            # add_subtitles_to_video will re-encode, so it becomes the final output
            # We use ready_video as input because it has the mixed audio
            add_subtitles_to_video(
                ready_video,
                temp_subtitled,
                all_transcriptions,
                subtitle_offset=0.0
            )
            # Copy subtitled version to final output
            import shutil
            shutil.copy2(temp_subtitled, final_output)
        else:
            # Copy ready_video (which has music + crop) to final output
            import shutil
            shutil.copy2(ready_video, final_output)
        
        # Cleanup
        for f in [temp_stitched, temp_cropped, temp_subtitled, temp_with_music] + temp_clips:
            if os.path.exists(f): 
                try: os.remove(f)
                except: pass
            
        update_progress("Success!", 100)
        return {
            "success": True,
            "output_file": final_output,
            "video_title": f"Coherent Short {session_id}"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
