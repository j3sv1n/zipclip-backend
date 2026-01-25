from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip, vfx, ImageClip
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import re
from Components.Transcription import split_transcription_to_words

def create_styled_subtitle_image(text, width, fontsize, font_path=None):
    """
    Create a high-quality subtitle image with modern styling.
    
    Args:
        text: Subtitle text
        width: Image width
        fontsize: Font size
        font_path: Path to font file (optional)
    
    Returns:
        PIL Image with styled text
    """
    # Create image with transparency
    height = int(fontsize * 2.5)
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to load custom font, fallback to default
    try:
        if font_path:
            font = ImageFont.truetype(font_path, fontsize)
        else:
            # Try common bold fonts
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize)
    except:
        font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text horizontally, position in bottom half
    x = (width - text_width) // 2
    y = height // 3
    
    # Draw semi-transparent background rounded effect
    padding = 15
    bg_bbox = [x - padding, y - padding // 2, x + text_width + padding, y + text_height + padding // 2]
    
    # Draw dark background with slight transparency
    draw.rectangle(bg_bbox, fill=(0, 0, 0, 180))
    
    # Draw text with white color and subtle shadow
    shadow_offset = 2
    shadow_color = (0, 0, 0, 200)
    text_color = (255, 255, 255, 255)
    
    # Shadow effect
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
    
    # Main text with gradient-like effect using bright white
    draw.text((x, y), text, font=font, fill=text_color)
    
    return img

def add_subtitles_to_video(input_video, output_video, transcriptions, video_start_time=0, words_per_subtitle=2):
    """
    Add beautifully styled word-level subtitles to video.
    Shows 2-3 words at a time, synchronized with audio.
    
    Args:
        input_video: Path to input video file
        output_video: Path to output video file
        transcriptions: List of [text, start, end] from transcribeAudio
        video_start_time: Start time offset if video was cropped
        words_per_subtitle: Number of words to show at a time (default: 2)
    """
    video = VideoFileClip(input_video)
    video_duration = video.duration
    
    # Split transcriptions into word-level chunks
    word_level_subs = split_transcription_to_words(transcriptions, words_per_chunk=words_per_subtitle)
    
    # Filter subtitles to only those within the video timeframe
    relevant_subtitles = []
    for text, start, end in word_level_subs:
        # Adjust times relative to video start
        adjusted_start = start - video_start_time
        adjusted_end = end - video_start_time
        
        # Only include if within video duration
        if adjusted_end > 0 and adjusted_start < video_duration:
            adjusted_start = max(0, adjusted_start)
            adjusted_end = min(video_duration, adjusted_end)
            # Only add if duration is meaningful (at least 0.1 seconds)
            if adjusted_end - adjusted_start >= 0.1:
                relevant_subtitles.append([text.strip(), adjusted_start, adjusted_end])
    
    if not relevant_subtitles:
        print("No transcriptions found for this video segment")
        video.write_videofile(output_video, codec='libx264', audio_codec='aac')
        video.close()
        return
    
    # Create text clips for each subtitle chunk
    text_clips = []
    
    # Dynamic font sizing based on video height - reduced for better fit
    # Smaller than before to not be too huge
    dynamic_fontsize = int(video.h * 0.05)
    
    # Try to find a good bold font
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    font_path = None
    for path in font_paths:
        try:
            ImageFont.truetype(path, dynamic_fontsize)
            font_path = path
            break
        except:
            pass
    
    fade_duration = 0.1
    
    for idx, (text, start, end) in enumerate(relevant_subtitles):
        # Clean up text and convert to uppercase
        text = text.strip().upper()
        if not text:
            continue
        
        duration = end - start
        
        # Create styled subtitle image
        subtitle_img = create_styled_subtitle_image(text, video.w, dynamic_fontsize, font_path)
        
        # Convert PIL image to ImageClip
        txt_clip = ImageClip(np.array(subtitle_img))
        
        # Position in lower third (around 60% down from top, leaving room for bottom)
        txt_clip = txt_clip.set_position(('center', int(video.h * 0.60)))
        txt_clip = txt_clip.set_start(start)
        txt_clip = txt_clip.set_duration(duration)
        
        # Add smooth fade in/out animations if duration is long enough
        if duration > fade_duration * 2:
            txt_clip = txt_clip.fadein(fade_duration).fadeout(fade_duration)
        
        text_clips.append(txt_clip)
    
    # Composite video with subtitles
    print(f"Adding {len(text_clips)} beautifully styled subtitle chunks to video...")
    final_video = CompositeVideoClip([video] + text_clips)
    
    # Write output
    final_video.write_videofile(
        output_video,
        codec='libx264',
        audio_codec='aac',
        fps=video.fps,
        preset='medium',
        bitrate='3000k'
    )
    
    video.close()
    final_video.close()
    print(f"✓ Subtitles added successfully -> {output_video}")

