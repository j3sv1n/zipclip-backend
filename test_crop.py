import os
from moviepy.editor import ColorClip, concatenate_videoclips
from Components.FaceCrop import crop_to_vertical

INPUT = "test_input2.mp4"
OUTPUT = "test_cropped.mp4"

# Create a 4s test video with three colored sections
if not os.path.exists(INPUT):
    clips = [
        ColorClip(size=(640,360), color=(255,0,0)).set_duration(1.5),
        ColorClip(size=(640,360), color=(0,255,0)).set_duration(1.5),
        ColorClip(size=(640,360), color=(0,0,255)).set_duration(1.0),
    ]
    video = concatenate_videoclips(clips)
    video.write_videofile(INPUT, fps=24, codec='libx264', audio=False)
    video.close()

crop_to_vertical(INPUT, OUTPUT)
print('crop result done')
