from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight
from Components.FaceCrop import crop_to_vertical, combine_videos
from Components.Subtitles import add_subtitles_to_video

url = input("Enter YouTube video URL: ")
Vid= download_youtube_video(url)
if Vid:
    Vid = Vid.replace(".webm", ".mp4")
    print(f"Downloaded video and audio files successfully! at {Vid}")

    Audio = extractAudio(Vid)
    if Audio:

        transcriptions = transcribeAudio(Audio)
        if len(transcriptions) > 0:
            print(f"\n{'='*60}")
            print(f"TRANSCRIPTION SUMMARY: {len(transcriptions)} segments")
            print(f"{'='*60}\n")
            TransText = ""

            for text, start, end in transcriptions:
                TransText += (f"{start} - {end}: {text}")

            print("Analyzing transcription to find best highlight...")
            start , stop = GetHighlight(TransText)
            print(f"✓ Highlight selected: {start}s - {stop}s")
            #handle the case when the highlight starts from 0s
            if start>0 and stop>0 and stop>start:
                print(f"\nCreating short video: {start}s - {stop}s ({stop-start}s duration)")
                print(f"Start: {start} , End: {stop}")

                Output = "Out.mp4"

                print("Step 1/3: Extracting clip from original video...")
                crop_video(Vid, Output, start, stop)
                croped = "croped.mp4"

                print("Step 2/3: Cropping to vertical format (9:16)...")
                crop_to_vertical("Out.mp4", croped)
                
                print("Step 3/4: Adding subtitles to video...")
                croped_with_subs = "croped_subtitled.mp4"
                add_subtitles_to_video(croped, croped_with_subs, transcriptions, video_start_time=start)
                
                print("Step 4/4: Adding audio to final video...")
                combine_videos("Out.mp4", croped_with_subs, "Final.mp4")
                print(f"\n{'='*60}")
                print("✓ SUCCESS: Final.mp4 is ready!")
                print(f"{'='*60}\n")
            else:
                print("Error in getting highlight")
        else:
            print("No transcriptions found")
    else:
        print("No audio file found")
else:
    print("Unable to Download the video")