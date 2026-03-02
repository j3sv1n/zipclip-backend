from moviepy.editor import ColorClip, concatenate_videoclips
from Components.Edit import stitch_video_segments
import os

INP = "light_input.mp4"
OUT = "light_output.mp4"

# make two very different clips (high visual diff -> light leak)
if not os.path.exists(INP):
    a = ColorClip(size=(640,360), color=(255,0,0)).set_duration(2)   # red
    b = ColorClip(size=(640,360), color=(0,0,255)).set_duration(2)   # blue
    video = concatenate_videoclips([a, b])
    video.write_videofile(INP, fps=24, codec="libx264", audio=False)
    video.close()

segments = [
    {"start": 0.0, "end": 2.0},
    {"start": 2.0, "end": 4.0},
]

ok = stitch_video_segments(INP, segments, OUT)
print("result:", ok)
