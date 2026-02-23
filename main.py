from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video, stitch_video_segments
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight, GetHighlightMultiSegment, GetHighlightMultiSegmentFromScenes, GetHighlightMultiSegmentFromFrames
from Components.SceneDetection import detect_scenes, map_transcript_to_scenes, convert_scenes_to_segments, analyze_scenes_with_vision
from Components.FaceCrop import crop_to_vertical, combine_videos
from Components.Subtitles import add_subtitles_to_video
import sys
import os
import uuid
import re

# Generate unique session ID for this run (for concurrent execution support)
session_id = str(uuid.uuid4())[:8]
print(f"Session ID: {session_id}")

# Create output directories if they don't exist
output_dir = "output_videos"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created output directory: {output_dir}")

audio_dir = "audio"
if not os.path.exists(audio_dir):
    os.makedirs(audio_dir)
    print(f"Created audio directory: {audio_dir}")

# Check for auto-approve flag (for batch processing)
auto_approve = "--auto-approve" in sys.argv
if auto_approve:
    sys.argv.remove("--auto-approve")

# Check if URL/file was provided as command-line argument
if len(sys.argv) > 1:
    url_or_file = sys.argv[1]
    print(f"Using input from command line: {url_or_file}")
else:
    url_or_file = input("Enter YouTube video URL or local video file path: ")

# Check if input is a local file
video_title = None
if os.path.isfile(url_or_file):
    print(f"Using local video file: {url_or_file}")
    Vid = url_or_file
    # Extract title from filename
    video_title = os.path.splitext(os.path.basename(url_or_file))[0]
else:
    # Assume it's a YouTube URL
    print(f"Downloading from YouTube: {url_or_file}")
    Vid = download_youtube_video(url_or_file)
    if Vid:
        Vid = Vid.replace(".webm", ".mp4")
        print(f"Downloaded video and audio files successfully! at {Vid}")
        # Extract title from downloaded file path
        video_title = os.path.splitext(os.path.basename(Vid))[0]

# Ask user for processing mode
print(f"\n{'='*60}")
print("SELECT PROCESSING MODE:")
print(f"{'='*60}")
print("1. Continuous clip (original): Extract one continuous 120s segment")
print("2. Multi-segment (transcript): Extract multiple important segments from transcription")
print("3. Multi-segment (scene-based): Detect scenes and extract important ones")
mode_input = input("\nSelect mode (1-3, default: 1): ").strip()

if mode_input == '2':
    processing_mode = 'multi_segment'
elif mode_input == '3':
    processing_mode = 'scene_based'
else:
    processing_mode = 'continuous'

print(f"Processing mode: {processing_mode}\n")

# Ask user if they want subtitles
subtitles_input = input("Do you want to add subtitles to the video? (y/n, default: y): ").strip().lower()
add_subtitles = subtitles_input != 'n'  # Default to yes unless user explicitly says no

# Clean and slugify title for filename
def clean_filename(title):
    # Convert to lowercase
    cleaned = title.lower()
    # Remove or replace invalid filename characters
    cleaned = re.sub(r'[<>:"/\\|?*\[\]]', '', cleaned)
    # Replace spaces and underscores with hyphens
    cleaned = re.sub(r'[\s_]+', '-', cleaned)
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r'-+', '-', cleaned)
    # Remove leading/trailing hyphens
    cleaned = cleaned.strip('-')
    # Limit length
    return cleaned[:80]

# Process video (works for both local files and downloaded videos)
if Vid:
    # Create unique temporary filenames
    audio_file = os.path.join(audio_dir, f"audio_{session_id}.wav")
    temp_clip = f"temp_clip_{session_id}.mp4"
    temp_cropped = f"temp_cropped_{session_id}.mp4"
    temp_subtitled = f"temp_subtitled_{session_id}.mp4"
    
    Audio = extractAudio(Vid, audio_file)
    if Audio:

        transcriptions = transcribeAudio(Audio)
        if len(transcriptions) > 0:
            print(f"\n{'='*60}")
            print(f"TRANSCRIPTION SUMMARY: {len(transcriptions)} segments")
            print(f"{'='*60}\n")
            TransText = ""

            for segment in transcriptions:
                TransText += (f"{segment['start']} - {segment['end']}: {segment['text']}\n")

            # Route to appropriate processing mode
            segments = None
            
            if processing_mode == 'continuous':
                # Original mode: single continuous clip
                print("Analyzing transcription to find best continuous highlight...")
                start , stop = GetHighlight(TransText)
                
                # Check if GetHighlight failed
                if start is None or stop is None:
                    print(f"\n{'='*60}")
                    print("ERROR: Failed to get highlight from LLM")
                    print(f"{'='*60}")
                    print("This could be due to:")
                    print("  - OpenAI API issues or rate limiting")
                    print("  - Invalid API key")
                    print("  - Network connectivity problems")
                    print("  - Malformed transcription data")
                    print(f"\nTranscription summary:")
                    print(f"  Total segments: {len(transcriptions)}")
                    print(f"  Total length: {len(TransText)} characters")
                    print(f"{'='*60}\n")
                    sys.exit(1)
                
                segments = [{'start': start, 'end': stop}]
            
            elif processing_mode == 'multi_segment':
                # Multi-segment mode: select multiple segments from transcription
                print("Analyzing transcription to find multiple important segments...")
                segments = GetHighlightMultiSegment(TransText, target_duration=120)
                
                if segments is None:
                    print(f"\n{'='*60}")
                    print("ERROR: Failed to get segments from LLM")
                    print(f"{'='*60}\n")
                    sys.exit(1)
            
            elif processing_mode == 'scene_based':
                # Scene-based mode: detect scenes using frame analysis and select important ones
                print("Detecting scenes in video using frame-based analysis...")
                scenes = detect_scenes(Vid)
                
                if not scenes:
                    print(f"\n{'='*60}")
                    print("ERROR: Failed to detect scenes in video")
                    print(f"{'='*60}\n")
                    sys.exit(1)
                
                print("Analyzing scene content with visual AI...")
                scene_segments = analyze_scenes_with_vision(Vid, scenes)
                
                if not scene_segments:
                    print(f"\n{'='*60}")
                    print("ERROR: Failed to analyze scenes")
                    print(f"{'='*60}\n")
                    sys.exit(1)
                
                print("Selecting most important scenes based on visual content...")
                segments = GetHighlightMultiSegmentFromFrames(scene_segments, target_duration=120)
                
                if segments is None:
                    print(f"\n{'='*60}")
                    print("ERROR: Failed to select scenes from LLM")
                    print(f"{'='*60}\n")
                    sys.exit(1)
            
            # Interactive approval loop with timeout (skip if auto-approve)
            import select
            
            approved = auto_approve  # Auto-approve if flag is set
            
            if not auto_approve and segments:
                while not approved:
                    print(f"\n{'='*60}")
                    print(f"SELECTED SEGMENTS ({len(segments)} total):")
                    print(f"{'='*60}")
                    total_duration = 0
                    for i, seg in enumerate(segments, 1):
                        duration = seg['end'] - seg['start']
                        total_duration += duration
                        print(f"  Segment {i}: {seg['start']:.2f}s - {seg['end']:.2f}s ({duration:.2f}s)")
                    print(f"Total duration: {total_duration:.2f}s")
                    print(f"{'='*60}\n")
                    
                    print("Options:")
                    print("  [Enter/y] Approve and continue")
                    print("  [r] Regenerate selection")
                    print("  [n] Cancel")
                    print("\nAuto-approving in 15 seconds if no input...")
                    
                    try:
                        # Check if stdin is ready within 15 seconds
                        ready, _, _ = select.select([sys.stdin], [], [], 15)
                        if ready:
                            user_input = sys.stdin.readline().strip().lower()
                            if user_input == 'r':
                                print("\nRegenerating selection...")
                                if processing_mode == 'continuous':
                                    start, stop = GetHighlight(TransText)
                                    segments = [{'start': start, 'end': stop}]
                                elif processing_mode == 'multi_segment':
                                    segments = GetHighlightMultiSegment(TransText, target_duration=120)
                                elif processing_mode == 'scene_based':
                                    segments = GetHighlightMultiSegmentFromScenes(scene_transcripts, target_duration=120)
                            elif user_input == 'n':
                                print("Cancelled by user")
                                sys.exit(0)
                            else:
                                print("Approved by user")
                                approved = True
                        else:
                            print("\nTimeout - auto-approving selection")
                            approved = True
                    except:
                        # Fallback if select doesn't work (e.g., Windows)
                        print("\nAuto-approving (timeout not available on this platform)")
                        approved = True
            else:
                print(f"\n{'='*60}")
                print(f"SELECTED SEGMENTS ({len(segments) if segments else 0} total):")
                for i, seg in enumerate(segments or [], 1):
                    duration = seg['end'] - seg['start']
                    print(f"  Segment {i}: {seg['start']:.2f}s - {seg['end']:.2f}s ({duration:.2f}s)")
                print(f"{'='*60}")
                print("Auto-approved (batch mode)\n")
            
            # Process the selected segments
            if segments and len(segments) > 0:
                print(f"\n✓ Creating short video with {len(segments)} segment(s)...")
                
                # Generate final output filename with random identifier
                clean_title = clean_filename(video_title) if video_title else "output"
                final_output = os.path.join(output_dir, f"{clean_title}_{session_id}_short.mp4")
                temp_stitched = f"temp_stitched_{session_id}.mp4"
                
                if len(segments) == 1:
                    # Single segment: use simple crop
                    seg = segments[0]
                    print(f"Step 1/4: Extracting single segment ({seg['start']:.2f}s - {seg['end']:.2f}s)...")
                    crop_video(Vid, temp_clip, seg['start'], seg['end'])
                else:
                    # Multiple segments: stitch them together
                    print(f"Step 1/4: Stitching {len(segments)} segments together...")
                    if not stitch_video_segments(Vid, segments, temp_stitched):
                        print("ERROR: Failed to stitch video segments")
                        sys.exit(1)
                    temp_clip = temp_stitched

                print("Step 2/4: Cropping to vertical format (9:16)...")
                crop_to_vertical(temp_clip, temp_cropped)
                
                if add_subtitles:
                    print("Step 3/4: Adding subtitles to video...")
                    # Pass all segments for correct timing mapping
                    add_subtitles_to_video(
                        temp_cropped, 
                        temp_subtitled, 
                        transcriptions, 
                        segments=segments
                    )
                    
                    print("Step 4/4: Adding audio to final video...")
                    combine_videos(temp_clip, temp_subtitled, final_output)
                else:
                    print("Step 3/3: Adding audio to final video (subtitles skipped)...")
                    combine_videos(temp_clip, temp_cropped, final_output)
                
                print(f"\n{'='*60}")
                print(f"✓ SUCCESS: {final_output} is ready!")
                print(f"{'='*60}\n")
                
                # Clean up temporary files
                try:
                    temp_files = [audio_file, temp_clip, temp_cropped, temp_subtitled, temp_stitched]
                    for temp_file in temp_files:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    print(f"Cleaned up temporary files for session {session_id}")
                except Exception as e:
                    print(f"Warning: Could not clean up some temporary files: {e}")
            else:
                print("Error in processing segments")
        else:
            print("No transcriptions found")
    else:
        print("No audio file found")
else:
    print("Unable to process the video")