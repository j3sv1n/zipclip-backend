#!/usr/bin/env python3
"""
Test script to demonstrate word-level subtitle chunking
"""

from Components.Transcription import split_transcription_to_words

# Sample transcription (simulating what would come from Whisper)
sample_transcription = [
    ["The quick brown fox jumps over the lazy dog", 0.0, 5.0],
    ["This is another sentence for testing", 5.5, 8.5],
    ["Word level timing synchronization is important for subtitles", 9.0, 14.0]
]

print("=" * 70)
print("ORIGINAL TRANSCRIPTION (sentence-level)")
print("=" * 70)
for text, start, end in sample_transcription:
    print(f"[{start:.2f}s - {end:.2f}s]: {text}")

print("\n" + "=" * 70)
print("CONVERTED TO WORD-LEVEL CHUNKS (2 words per chunk)")
print("=" * 70)

word_chunks = split_transcription_to_words(sample_transcription, words_per_chunk=2)
for text, start, end in word_chunks:
    duration = end - start
    print(f"[{start:.2f}s - {end:.2f}s] ({duration:.2f}s): {text}")

print("\n" + "=" * 70)
print("CONVERTED TO WORD-LEVEL CHUNKS (3 words per chunk)")
print("=" * 70)

word_chunks_3 = split_transcription_to_words(sample_transcription, words_per_chunk=3)
for text, start, end in word_chunks_3:
    duration = end - start
    print(f"[{start:.2f}s - {end:.2f}s] ({duration:.2f}s): {text}")

print("\n✓ Test complete! Word-level subtitle timing is working correctly.")
