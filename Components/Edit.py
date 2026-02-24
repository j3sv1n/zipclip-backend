from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip, vfx
import subprocess
import numpy as np

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
        print("  Determining intelligent transitions and building timeline...")

        # Helper: get a representative frame from a clip (time offset seconds from start)
        def _get_frame_safe(clip, t_offset=0.1):
            try:
                t = min(max(t_offset, 0), max(0, clip.duration - 0.01))
                return clip.get_frame(t)
            except Exception:
                return None

        # Helper: compute normalized mean absolute difference between two frames
        def _frame_diff(f1, f2):
            if f1 is None or f2 is None:
                return 1.0
            try:
                f1 = f1.astype('float32') / 255.0
                f2 = f2.astype('float32') / 255.0
                return float(np.mean(np.abs(f1 - f2)))
            except Exception:
                return 1.0

        # Decide transition type between two clips
        def _choose_transition(clip_a, clip_b):
            # Very short clips => hard cut
            if clip_a.duration < 1.5 or clip_b.duration < 1.5:
                return ('cut', 0)

            # Compute difference between last frame of A and first frame of B
            frame_a = None
            frame_b = None
            try:
                frame_a = clip_a.get_frame(max(0, clip_a.duration - 0.05))
            except Exception:
                frame_a = _get_frame_safe(clip_a, clip_a.duration/2 if clip_a.duration>0 else 0)
            try:
                frame_b = clip_b.get_frame(0.05)
            except Exception:
                frame_b = _get_frame_safe(clip_b, 0.1)

            diff = _frame_diff(frame_a, frame_b)

            # Very similar frames -> cross-dissolve
            if diff < 0.06:
                return ('crossfade', min(1.0, clip_a.duration/3, clip_b.duration/3))

            # Moderate similarity -> simple fade
            if diff < 0.18:
                return ('fade', min(1.0, clip_a.duration/3, clip_b.duration/3))

            # Very different -> occasional light leak to hide abrupt change
            return ('light_leak', min(0.8, clip_a.duration/4, clip_b.duration/4))

        # Expand clips slightly to accommodate transitions where possible
        expanded_clips = []
        clip_meta = []

        for i, segment in enumerate(segments):
            start = max(0, segment['start'])
            end = min(max_time, segment['end'])
            # We will expand by up to 1s on either side if possible; exact overlap depends on neighbors
            expanded_clips.append({'start': start, 'end': end})

        # Pre-extract raw clips (we'll adjust starts when building timeline)
        raw_clips = []
        for seg in expanded_clips:
            clip = video.subclip(seg['start'], seg['end']).fx(vfx.freeze, t=0) if False else video.subclip(seg['start'], seg['end'])
            raw_clips.append(clip)

        # Build timeline with start times and overlays
        timeline_clips = []
        overlays = []
        current_time = 0.0

        for i, clip in enumerate(raw_clips):
            if i == 0:
                # first clip starts at 0
                clip_start = 0.0
                timeline_clips.append(clip.set_start(clip_start))
                current_time = clip_start + clip.duration
                continue

            prev = raw_clips[i-1]
            trans_type, trans_dur = _choose_transition(prev, clip)

            if trans_type == 'cut' or trans_dur <= 0:
                # hard cut
                clip_start = current_time
                timeline_clips.append(clip.set_start(clip_start))
                current_time = clip_start + clip.duration

            elif trans_type == 'fade':
                # apply fade out to previous and fade in to next without overlap
                prev_faded = timeline_clips[-1].fx(vfx.fadeout, trans_dur)
                timeline_clips[-1] = prev_faded
                clip_faded = clip.fx(vfx.fadein, trans_dur)
                clip_start = current_time
                timeline_clips.append(clip_faded.set_start(clip_start))
                current_time = clip_start + clip.duration

            elif trans_type == 'crossfade':
                # Overlap clips by trans_dur
                # reposition current clip so it starts trans_dur before prev ends
                clip_start = current_time - trans_dur
                if clip_start < 0:
                    clip_start = 0
                # ensure crossfadein applied to incoming clip
                clip_cf = clip.crossfadein(trans_dur)
                timeline_clips.append(clip_cf.set_start(clip_start))
                current_time = clip_start + clip.duration

            elif trans_type == 'light_leak':
                # Do a short crossfade and add a white flash overlay
                leak_dur = trans_dur
                clip_start = current_time - leak_dur/2
                if clip_start < 0:
                    clip_start = 0
                clip_cf = clip.crossfadein(leak_dur/2)
                timeline_clips.append(clip_cf.set_start(clip_start))
                # overlay: white ColorClip with quick fade in/out
                try:
                    w, h = clip.size
                except Exception:
                    w, h = video.size
                leak = ColorClip(size=(w, h), color=(255, 200, 150)).set_opacity(0.0)
                leak = leak.set_start(max(0, clip_start)).set_duration(leak_dur)
                leak = leak.fx(vfx.fadein, leak_dur*0.25).fx(vfx.fadeout, leak_dur*0.6)
                overlays.append(leak)
                current_time = clip_start + clip.duration

            else:
                # fallback to hard cut
                clip_start = current_time
                timeline_clips.append(clip.set_start(clip_start))
                current_time = clip_start + clip.duration

        # Create final composite clip
        print(f"  Creating composite timeline with {len(timeline_clips)} clips and {len(overlays)} overlays")
        all_clips = timeline_clips + overlays
        final_comp = CompositeVideoClip(all_clips, size=video.size)

        print(f"  Writing stitched video to {output_file}...")
        final_comp.write_videofile(output_file, codec='libx264', audio_codec='aac')

        # Clean up
        final_comp.close()
        for c in raw_clips:
            try:
                c.close()
            except Exception:
                pass
        video.close()

        print(f"✓ Successfully stitched {len(clips)} segments with transitions")
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

