from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import VideoFileClip, concatenate_videoclips
import subprocess

def extractAudio(video_path, audio_path="audio.wav"):
    try:
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()
        print(f"Extracted audio to: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"An error occurred while extracting audio: {e}")
        return None


def crop_video(input_file, output_file, start_time, end_time):
    with VideoFileClip(input_file) as video:
        # Ensure end_time doesn't exceed video duration
        max_time = video.duration - 0.1  # Small buffer to avoid edge cases
        if end_time > max_time:
            print(f"Warning: Requested end time ({end_time}s) exceeds video duration ({video.duration}s). Capping to {max_time}s")
            end_time = max_time
        
        cropped_video = video.subclip(start_time, end_time)
        cropped_video.write_videofile(output_file, codec='libx264')


def stitch_video_segments(input_file, segments, output_file):
    """
    Extract multiple segments from a video and stitch them together.
    
    Args:
        input_file: Path to the input video file
        segments: List of dicts with 'start' and 'end' keys, e.g. [{'start': 10.5, 'end': 25.0}, ...]
        output_file: Path for the output stitched video
    
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"\nStitching {len(segments)} video segments...")
        video = VideoFileClip(input_file)
        max_time = video.duration - 0.1
        
        # Extract each segment as a subclip
        clips = []
        total_duration = 0
        
        for i, segment in enumerate(segments):
            start = segment['start']
            end = segment['end']
            
            # Validate times
            if end > max_time:
                print(f"  Warning: Segment {i+1} end time ({end}s) exceeds video duration. Capping to {max_time}s")
                end = max_time
            
            if start >= end:
                print(f"  Warning: Skipping invalid segment {i+1} (start={start}s, end={end}s)")
                continue
            
            print(f"  Extracting segment {i+1}/{len(segments)}: {start:.2f}s - {end:.2f}s ({end-start:.2f}s)")
            clip = video.subclip(start, end)
            clips.append(clip)
            total_duration += (end - start)
        
        if not clips:
            print("Error: No valid clips to stitch")
            video.close()
            return False
        
        print(f"  Total duration of stitched video: {total_duration:.2f}s")
        print("  Concatenating clips...")
        
        # Concatenate all clips
        final_clip = concatenate_videoclips(clips, method="compose")
        
        print(f"  Writing stitched video to {output_file}...")
        final_clip.write_videofile(output_file, codec='libx264', audio_codec='aac')
        
        # Clean up
        final_clip.close()
        video.close()
        
        print(f"✓ Successfully stitched {len(clips)} segments")
        return True
        
    except Exception as e:
        print(f"Error stitching video segments: {e}")
        import traceback
        traceback.print_exc()
        return False

# Example usage:
if __name__ == "__main__":
    input_file = r"Example.mp4" ## Test
    print(input_file)
    output_file = "Short.mp4"
    start_time = 31.92 
    end_time = 49.2   

    crop_video(input_file, output_file, start_time, end_time)

