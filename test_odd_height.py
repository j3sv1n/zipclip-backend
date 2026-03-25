import os
import cv2
import time
from moviepy.editor import VideoFileClip

# Create an empty file to simulate VideoWriter failing silently
with open("test_empty.mp4", "w") as f:
    pass

print("Before VideoFileClip...")
try:
    c = VideoFileClip("test_empty.mp4")
except Exception as e:
    print(f"Exception: {e}")
print("After VideoFileClip.")

