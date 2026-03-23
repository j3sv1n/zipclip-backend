from moviepy.editor import ColorClip, VideoClip, CompositeVideoClip
import numpy as np

w, h = 640, 480
duration = 2

def make_mask(t):
    return np.ones((h, w), dtype=float) * 0.5  # 50% opacity

def make_mask_uint8(t):
    return (np.ones((h, w)) * 128).astype('uint8')

color_clip = ColorClip(size=(w, h), color=(255,0,0)).set_duration(duration)
bg_clip = ColorClip(size=(w, h), color=(0,0,255)).set_duration(duration)

# float mask
mask1 = VideoClip(make_mask, ismask=True).set_duration(duration)
# uint8 mask
mask2 = VideoClip(make_mask_uint8, ismask=True).set_duration(duration)

try:
    c1 = color_clip.set_mask(mask1)
    comp1 = CompositeVideoClip([bg_clip, c1])
    frame1 = comp1.get_frame(1.0)
    print("Float mask frame test: success", frame1[0,0])
except Exception as e:
    print("Float mask failed:", e)

try:
    c2 = color_clip.set_mask(mask2)
    comp2 = CompositeVideoClip([bg_clip, c2])
    frame2 = comp2.get_frame(1.0)
    print("uint8 mask frame test: success", frame2[0,0])
except Exception as e:
    print("uint8 mask failed:", e)
