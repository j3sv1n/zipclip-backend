from moviepy.editor import ColorClip
from moviepy.video.fx.all import crop, resize

cw, ch = 3000, 4000
tw, th = 1080, 1920

clip = ColorClip(size=(cw, ch), color=(255,0,0)).set_duration(1)
if cw/ch > tw/th:
    clip = resize(clip, height=th)
else:
    clip = resize(clip, width=tw)

clip = crop(clip, x_center=clip.w/2, y_center=clip.h/2, width=tw, height=th)
print(f"Final size: {clip.size}")
