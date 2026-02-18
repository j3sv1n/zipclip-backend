from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip, vfx, ImageClip
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import re
import os
from Components.Transcription import split_transcription_to_words

def create_styled_subtitle_image(text_data, width, fontsize, font_path=None, active_word_index=None):
    """
    Create a high-quality subtitle image with modern styling and word highlighting.
    
    Args:
        text_data: Either a string or a list of words
        width: Image width
        fontsize: Font size
        font_path: Path to font file
        active_word_index: Index of the word to highlight (if text_data is a list)
    
    Returns:
        PIL Image
    """
    height = int(fontsize * 3)
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        if font_path:
            font = ImageFont.truetype(font_path, fontsize)
            bold_font = ImageFont.truetype(font_path, int(fontsize * 1.1))
        else:
            # Try liberation bold as a primary choice for a professional look
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", fontsize)
            bold_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", int(fontsize * 1.1))
    except:
        font = ImageFont.load_default()
        bold_font = font

    # Process text into words
    if isinstance(text_data, str):
        words = text_data.split()
    else:
        words = text_data

    # Calculate total width to center the whole line
    # We use bold_font for measurements to have a consistent center
    word_spacings = [draw.textbbox((0, 0), w, font=bold_font)[2] for w in words]
    space_width = draw.textbbox((0, 0), " ", font=bold_font)[2]
    total_text_width = sum(word_spacings) + (space_width * (len(words) - 1))
    
    start_x = (width - total_text_width) // 2
    y = height // 4
    
    # Draw dropshadow for the whole line first
    curr_x = start_x
    for i, word in enumerate(words):
        draw.text((curr_x + 4, y + 4), word, font=bold_font, fill=(0, 0, 0, 150))
        curr_x += word_spacings[i] + space_width

    # Draw words with stroke and highlight
    curr_x = start_x
    for i, word in enumerate(words):
        is_active = (active_word_index == i)
        
        # Style settings
        fill_color = (255, 255, 255) # White default
        if is_active:
            fill_color = (255, 255, 0) # Yellow highlight
            f = bold_font
        else:
            f = font
            
        # Draw stroke (outline) manually for maximum thickness and control
        stroke_color = (0, 0, 0)
        stroke_width = 3
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                if offset_x**2 + offset_y**2 <= stroke_width**2:
                    draw.text((curr_x + offset_x, y + offset_y), word, font=f, fill=stroke_color)
        
        # Draw main text
        draw.text((curr_x, y), word, font=f, fill=fill_color)
        
        curr_x += word_spacings[i] + space_width
    
    return img

def add_subtitles_to_video(input_video, output_video, transcriptions, segments=None, video_start_time=0, words_per_subtitle=2, subtitle_offset=0.0):
    """
    Add beautifully styled word-level subtitles to video with precise timing and highlighting.
    Supports multi-segment mapping if 'segments' is provided.
    """
    video = VideoFileClip(input_video)
    video_duration = video.duration
    
    # If segments are not provided, treat it as a single segment from video_start_time
    if not segments:
        segments = [{'start': video_start_time, 'end': video_start_time + video_duration}]
    
    # Pre-calculate segment offsets in the final stitched video
    segment_mappings = []
    current_stitched_time = 0
    for seg in segments:
        duration = seg['end'] - seg['start']
        segment_mappings.append({
            'global_start': seg['start'],
            'global_end': seg['end'],
            'stitched_start': current_stitched_time,
            'duration': duration
        })
        current_stitched_time += duration

    def map_to_stitched_time(global_time):
        global_time += subtitle_offset
        for mapping in segment_mappings:
            if mapping['global_start'] <= global_time <= mapping['global_end']:
                return mapping['stitched_start'] + (global_time - mapping['global_start'])
        return None

    # Group transcriptions into small chunks
    word_chunks = split_transcription_to_words(transcriptions, words_per_chunk=words_per_subtitle)
    
    text_clips = []
    dynamic_fontsize = int(video.h * 0.08) 
    
    font_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    font_path = next((p for p in font_paths if os.path.exists(p)), None)

    print(f"Generating {len(word_chunks)} subtitle chunks with multi-segment precision...")
    
    for chunk in word_chunks:
        # Map global chunk timing to stitched timing
        chunk_start = map_to_stitched_time(chunk['start'])
        chunk_end = map_to_stitched_time(chunk['end'])
        
        # Skip if chunk is not within any segment or outside video timeframe
        if chunk_start is None or chunk_end is None:
            continue
            
        chunk_start = max(0, chunk_start)
        chunk_end = min(video_duration, chunk_end)
        
        if chunk_end <= chunk_start:
            continue

        # If we have precise word timings, create a sub-clip for each word highlight
        if chunk.get('word_timings') and len(chunk['word_timings']) > 0:
            for i, word_data in enumerate(chunk['word_timings']):
                w_start = map_to_stitched_time(word_data['start'])
                w_end = map_to_stitched_time(word_data['end'])
                
                if w_start is None or w_end is None:
                    continue

                # Clip to chunk boundaries
                w_start = max(chunk_start, w_start)
                w_end = min(chunk_end, w_end)
                w_dur = w_end - w_start
                
                if w_dur <= 0.01: continue
                
                # Create image with the i-th word highlighted
                img = create_styled_subtitle_image(chunk['all_words'], video.w, dynamic_fontsize, font_path, active_word_index=i)
                txt_clip = ImageClip(np.array(img)).set_start(w_start).set_duration(w_dur)
                
                # Position in lower third
                txt_clip = txt_clip.set_position(('center', int(video.h * 0.65)))
                text_clips.append(txt_clip)
        else:
            # Fallback for chunks without precise timings
            duration = chunk_end - chunk_start
            if duration <= 0: continue
            
            img = create_styled_subtitle_image(chunk['text'], video.w, dynamic_fontsize, font_path)
            txt_clip = ImageClip(np.array(img)).set_start(chunk_start).set_duration(duration)
            txt_clip = txt_clip.set_position(('center', int(video.h * 0.65)))
            text_clips.append(txt_clip)

    if not text_clips:
        print("No transcriptions within video timeframe. Writing original video.")
        video.write_videofile(output_video, codec='libx264', audio_codec='aac')
    else:
        print(f"Compositing {len(text_clips)} subtitle elements...")
        # Sort clips by start time
        text_clips.sort(key=lambda x: x.start)
        final_video = CompositeVideoClip([video] + text_clips)
        
        # Write output with good performance settings
        final_video.write_videofile(
            output_video,
            codec='libx264',
            audio_codec='aac',
            fps=video.fps,
            preset='ultrafast',
            threads=4
        )
        final_video.close()
    
    video.close()

