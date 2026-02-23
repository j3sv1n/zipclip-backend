from faster_whisper import WhisperModel
import torch

def transcribeAudio(audio_path):
    try:
        print("Transcribing audio...")
        Device = "cuda" if torch.cuda.is_available() else "cpu"
        print(Device)
        model = WhisperModel("base.en", device="cuda" if torch.cuda.is_available() else "cpu")
        print("Model loaded")
        segments, info = model.transcribe(audio=audio_path, beam_size=5, language="en", max_new_tokens=128, condition_on_previous_text=False, word_timestamps=True)
        segments = list(segments)
        
        extracted_texts = []
        for segment in segments:
            # Extract word-level details if available
            words = []
            if segment.words:
                for word in segment.words:
                    words.append({
                        "text": word.word,
                        "start": word.start,
                        "end": word.end
                    })
            
            extracted_texts.append({
                "text": segment.text.strip(),
                "start": segment.start,
                "end": segment.end,
                "words": words
            })
            
        print(f"✓ Transcription complete: {len(extracted_texts)} segments extracted")
        return extracted_texts
    except Exception as e:
        print("Transcription Error:", e)
        return []

def split_transcription_to_words(transcriptions, words_per_chunk=2):
    """
    Split transcription segments into chunks of words using PRECISE word-level timing.
    
    Args:
        transcriptions: List of dicts with 'text', 'start', 'end', and 'words'
        words_per_chunk: Number of words to group together
    
    Returns:
        List of dicts with 'text', 'start', 'end', and 'highlight_word_index'
    """
    word_chunks = []
    
    for segment in transcriptions:
        words = segment.get('words', [])
        
        # Fallback to linear split if word timestamps are missing
        if not words:
            text_words = segment['text'].split()
            if not text_words: continue
            
            duration = segment['end'] - segment['start']
            time_per_word = duration / len(text_words)
            
            for i in range(0, len(text_words), words_per_chunk):
                chunk = text_words[i:i + words_per_chunk]
                word_chunks.append({
                    "text": " ".join(chunk),
                    "start": segment['start'] + (i * time_per_word),
                    "end": segment['start'] + ((i + len(chunk)) * time_per_word),
                    "all_words": chunk,
                    "word_timings": [] # No precise timings
                })
            continue

        # Use precise word timestamps
        for i in range(0, len(words), words_per_chunk):
            chunk_data = words[i:i + words_per_chunk]
            chunk_text = " ".join([w['text'].strip() for w in chunk_data])
            
            word_chunks.append({
                "text": chunk_text,
                "start": chunk_data[0]['start'],
                "end": chunk_data[-1]['end'],
                "all_words": [w['text'].strip() for w in chunk_data],
                "word_timings": chunk_data
            })
    
    return word_chunks

if __name__ == "__main__":
    audio_path = "audio.wav"
    transcriptions = transcribeAudio(audio_path)
    # print("Done")
    TransText = ""

    for segment in transcriptions:
        TransText += (f"{segment['start']} - {segment['end']}: {segment['text']}\n")
    print(TransText)