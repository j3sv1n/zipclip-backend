import cv2
import numpy as np
from moviepy.editor import *
from Components.Speaker import detect_faces_and_speakers, Frames
global Fps

def crop_to_vertical(input_video_path, output_video_path):
    """Crop video to vertical 9:16 format with static face detection (no tracking)"""
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    cap = cv2.VideoCapture(input_video_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    vertical_height = int(original_height)
    vertical_width = int(vertical_height * 9 / 16)
    print(f"Output dimensions: {vertical_width}x{vertical_height}")

    if original_width < vertical_width:
        print("Error: Original video width is less than the desired vertical width.")
        return

    # Detect face position in first 30 frames to determine static crop position
    print("Detecting face position for static crop...")
    face_positions = []
    for i in range(min(30, total_frames)):
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) > 0:
            # Get largest face
            best_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = best_face
            face_center_x = x + w // 2
            face_positions.append(face_center_x)
    
    # Calculate static crop position
    if face_positions:
        # Use median face position for stability
        avg_face_x = int(sorted(face_positions)[len(face_positions) // 2])
        # Offset slightly to the right to prevent right-side cutoff
        avg_face_x += 60
        x_start = max(0, min(avg_face_x - vertical_width // 2, original_width - vertical_width))
        print(f"Face detected. Using static crop at x={x_start}")
    else:
        # No face detected, use center crop
        x_start = (original_width - vertical_width) // 2
        print(f"No face detected. Using center crop at x={x_start}")
    
    x_end = x_start + vertical_width

    # Reset video to beginning
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # Write output with static crop
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (vertical_width, vertical_height))
    global Fps
    Fps = fps

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Apply static crop
        cropped_frame = frame[:, x_start:x_end]
        
        if cropped_frame.shape[1] == 0:
            print(f"Warning: Empty crop at frame {frame_count}")
            break
        
        out.write(cropped_frame)
        frame_count += 1
        
        if frame_count % 100 == 0:
            print(f"Processed {frame_count}/{total_frames} frames")

    cap.release()
    out.release()
    print(f"Cropping complete. Processed {frame_count} frames -> {output_video_path}")



def combine_videos(video_with_audio, video_without_audio, output_filename):
    try:
        # Load video clips
        clip_with_audio = VideoFileClip(video_with_audio)
        clip_without_audio = VideoFileClip(video_without_audio)

        audio = clip_with_audio.audio

        combined_clip = clip_without_audio.set_audio(audio)

        global Fps
        combined_clip.write_videofile(output_filename, codec='libx264', audio_codec='aac', fps=Fps, preset='medium', bitrate='3000k')
        print(f"Combined video saved successfully as {output_filename}")
    
    except Exception as e:
        print(f"Error combining video and audio: {str(e)}")



if __name__ == "__main__":
    input_video_path = r'Out.mp4'
    output_video_path = 'Croped_output_video.mp4'
    final_video_path = 'final_video_with_audio.mp4'
    detect_faces_and_speakers(input_video_path, "DecOut.mp4")
    crop_to_vertical(input_video_path, output_video_path)
    combine_videos(input_video_path, output_video_path, final_video_path)



