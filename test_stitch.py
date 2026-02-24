from moviepy.editor import ColorClip, concatenate_videoclips
from Components.Edit import stitch_video_segments
import os

INPUT = "test_input.mp4"
OUTPUT = "test_output.mp4"

# Create a 6s test video with three colored sections
if not os.path.exists(INPUT):
    clips = [
        ColorClip(size=(320,240), color=(255,0,0)).set_duration(2),
        ColorClip(size=(320,240), color=(0,255,0)).set_duration(2),
        ColorClip(size=(320,240), color=(0,0,255)).set_duration(2),
    ]
    video = concatenate_videoclips(clips)
    video.write_videofile(INPUT, fps=24, codec='libx264', audio=False)
    video.close()

segments = [
    {'start': 0.0, 'end': 2.0},
    {'start': 2.0, 'end': 4.0},
    {'start': 4.0, 'end': 6.0},
]

ok = stitch_video_segments(INPUT, segments, OUTPUT)
print('stitch result:', ok)
