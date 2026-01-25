from faster_whisper import WhisperModel
import torch

def transcribeAudio(audio_path):
    try:
        print("Transcribing audio...")
        Device = "cuda" if torch.cuda.is_available() else "cpu"
        print(Device)
        model = WhisperModel("base.en", device="cuda" if torch.cuda.is_available() else "cpu")
        print("Model loaded")
        segments, info = model.transcribe(audio=audio_path, beam_size=5, language="en", max_new_tokens=128, condition_on_previous_text=False)
        segments = list(segments)
        # print(segments)
        extracted_texts = [[segment.text, segment.start, segment.end] for segment in segments]
        print(f"✓ Transcription complete: {len(extracted_texts)} segments extracted")
        return extracted_texts
    except Exception as e:
        print("Transcription Error:", e)
        return []

def split_transcription_to_words(transcriptions, words_per_chunk=2):
    """
    Split transcription segments into chunks of 2-3 words with word-level timing.
    
    Args:
        transcriptions: List of [text, start, end] from transcribeAudio
        words_per_chunk: Number of words to group together (default: 2)
    
    Returns:
        List of [text, start, end] with word-level timing
    """
    word_chunks = []
    
    for text, segment_start, segment_end in transcriptions:
        # Split text into words
        words = text.strip().split()
        if not words:
            continue
        
        # Calculate time per word
        segment_duration = segment_end - segment_start
        time_per_word = segment_duration / len(words) if words else 0
        
        # Group words into chunks
        for i in range(0, len(words), words_per_chunk):
            chunk_words = words[i:i + words_per_chunk]
            chunk_text = ' '.join(chunk_words)
            
            # Calculate timing for this chunk
            chunk_start = segment_start + (i * time_per_word)
            chunk_end = segment_start + ((i + len(chunk_words)) * time_per_word)
            
            word_chunks.append([chunk_text, chunk_start, chunk_end])
    
    return word_chunks

if __name__ == "__main__":
    audio_path = "audio.wav"
    transcriptions = transcribeAudio(audio_path)
    # print("Done")
    TransText = ""

    for text, start, end in transcriptions:
        TransText += (f"{start} - {end}: {text}")
    print(TransText)