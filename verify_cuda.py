import torch
from faster_whisper import WhisperModel
import os

def test_cuda():
    print("Checking CUDA availability...")
    if torch.cuda.is_available():
        print(f"CUDA is available: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA is NOT available.")
        return

    print("Loading WhisperModel on CUDA...")
    try:
        model = WhisperModel("tiny", device="cuda", compute_type="float16")
        print("Model loaded successfully.")
        
        # Create a dummy audio file
        import wave
        with wave.open("test_audio.wav", "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(b'\x00' * 32000) # 2 seconds of silence
            
        print("Transcribing dummy audio...")
        segments, info = model.transcribe("test_audio.wav")
        print("Transcription started successfully.")
        for segment in segments:
            pass
        print("Transcription completed successfully.")
        
        os.remove("test_audio.wav")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cuda()
