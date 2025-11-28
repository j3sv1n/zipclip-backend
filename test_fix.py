from Components.FaceCrop import crop_to_vertical
import os
import glob

# Find the video file
video_files = glob.glob("videos/*.mp4")
if not video_files:
    print("No video files found in videos/")
    exit(1)

input_video = video_files[0]
output_video = "test_vertical.mp4"

print(f"Testing crop_to_vertical with {input_video}...")
try:
    crop_to_vertical(input_video, output_video)
    print("crop_to_vertical completed successfully.")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
