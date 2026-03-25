import os
from Components.FaceCrop import crop_to_vertical
print("Making dummy video...")
os.system("ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 -c:v libx264 -y test_input.mp4")
print("Cropping...")
crop_to_vertical("test_input.mp4", "test_output.mp4")
print("Done!")
