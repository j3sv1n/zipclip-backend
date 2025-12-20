# ZipClip - Scene Detection & Multi-Segment User Guide

## Quick Start

### Installation

```bash
# Install or update dependencies
pip install -r requirements.txt
```

### Running the App

```bash
# With local video file
python main.py /path/to/video.mp4

# With YouTube URL
python main.py "https://www.youtube.com/watch?v=..."

# Batch mode (auto-approve all selections)
python main.py /path/to/video.mp4 --auto-approve
```

## Processing Modes

When you run the app, you'll be prompted to choose a processing mode:

### Mode 1: Continuous Clip (Original)
**Best for:** Quick processing, simple videos, when you know the interesting part is in one continuous segment

- Analyzes the entire transcription
- Selects ONE continuous 120-second segment
- Uses the original algorithm
- Fastest to process

**Example workflow:**
```
Select mode (1-3, default: 1): 1
LLM analyzing transcription...
SELECTED SEGMENT: 45.2s - 165.2s (120s duration)
Approve and continue? [Enter/y]: y
```

---

### Mode 2: Multi-Segment (Transcript-based)
**Best for:** Content with multiple important points, educational videos, interview compilations

- Analyzes the entire transcription
- Selects 3-5 important segments scattered throughout the video
- Creates a cohesive narrative by combining segments
- Total duration targeted at 120 seconds

**Example workflow:**
```
Select mode (1-3, default: 1): 2
Analyzing transcription to find multiple important segments...
SELECTED 4 SEGMENTS:
  Segment 1: 12.45s - 28.30s (15.85s)
  Segment 2: 45.60s - 62.15s (16.55s)
  Segment 3: 120.30s - 138.45s (18.15s)
  Segment 4: 215.60s - 232.30s (16.70s)
Total duration: 67.25s

Approve and continue? [Enter/y]: y
```

**Pros:**
- ✅ Captures the best moments from the entire video
- ✅ No important parts missed due to being outside a 120s window
- ✅ LLM ensures segments complement each other
- ✅ More engaging final product

**Cons:**
- ⚠️ Slower processing (multiple segments to stitch)
- ⚠️ Segments may feel disconnected if not well-chosen
- ⚠️ Requires good LLM performance

---

### Mode 3: Multi-Segment (Scene-based)
**Best for:** Talking-head videos, presentations, videos with clear visual scenes

- Detects visual scene boundaries in the video
- Maps transcription to detected scenes
- Selects 3-5 important scenes
- Preserves natural scene breaks
- Total duration targeted at 120 seconds

**Example workflow:**
```
Select mode (1-3, default: 1): 3
Detecting scenes in video... (threshold=27.0, min_scene_len=3.0s)
✓ Detected 24 scenes in the video
Mapping transcriptions to detected scenes...
✓ Mapped 24 scenes with transcripts
Analyzing scenes to find important ones...
SELECTED 5 SCENES:
  Scene 1: 5.20s - 18.50s (13.30s)
    Reason: Speaker introduces main topic
  Scene 2: 45.10s - 68.30s (23.20s)
    Reason: Key insight explained with examples
  Scene 3: 120.45s - 142.80s (22.35s)
    Reason: Surprising discovery revealed
  Scene 4: 180.60s - 198.90s (18.30s)
    Reason: Practical tips and actionable advice
  Scene 5: 240.10s - 258.40s (18.30s)
    Reason: Conclusion and call to action

Total duration: 95.45s

Approve and continue? [Enter/y]: y
```

**Pros:**
- ✅ Respects visual narrative structure
- ✅ No awkward cuts within scenes
- ✅ Natural pacing and flow
- ✅ Good for presentation/talking-head content

**Cons:**
- ⚠️ Requires FFMPEG with libav support
- ⚠️ May require tuning scene detection parameters
- ⚠️ Less effective for fast-cut or montage videos

---

## Interactive Approval Loop

After segments are selected, you have three options:

```
Options:
  [Enter/y] Approve and continue
  [r] Regenerate selection
  [n] Cancel

Auto-approving in 15 seconds if no input...
```

### Regenerate
Press `r` to regenerate the selection:
- Uses the same mode but with different LLM sampling
- Useful if the first selection doesn't look good
- Can regenerate multiple times

### Batch Mode
Use the `--auto-approve` flag to skip the approval loop:
```bash
python main.py video.mp4 --auto-approve
```

---

## Processing Pipeline

Regardless of which mode you choose, here's what happens next:

### Step 1: Segment Extraction
- **Continuous mode**: Extracts one video clip
- **Multi-segment modes**: Extracts multiple clips and stitches them together

### Step 2: Vertical Cropping
- Crops video to 9:16 aspect ratio (TikTok/Instagram format)
- Intelligently detects faces and centers on speaker
- Falls back to half-width if no face detected (screen recordings)

### Step 3: Subtitle Generation (Optional)
- Automatically transcripts matching segments
- Burns subtitles into the video
- Skip with: `Do you want to add subtitles? (y/n): n`

### Step 4: Audio Merge
- Extracts original audio from input video
- Applies to final edited video
- Maintains audio quality

---

## Output

The final short is saved as:
```
{video-title}_{session-id}_short.mp4
```

Example:
```
life-is-short-ep-33_a1b2c3d4_short.mp4
```

---

## Advanced Usage

### Adjusting Scene Detection Sensitivity

Scene detection parameters can be modified in `Components/SceneDetection.py`:

```python
# Lower threshold = more scenes detected (more sensitive)
# Default: threshold=27.0
scenes = detect_scenes(video_path, threshold=20.0)  # More sensitive
scenes = detect_scenes(video_path, threshold=35.0)  # Less sensitive
```

### Target Duration

By default, all multi-segment modes target 120 seconds. To change:

Modify in `main.py` (around line 180):
```python
segments = GetHighlightMultiSegment(TransText, target_duration=90)  # 90 seconds
segments = GetHighlightMultiSegmentFromScenes(scene_transcripts, target_duration=180)  # 3 minutes
```

### Custom LLM Parameters

Edit `Components/LanguageTasks.py` to adjust LLM behavior:

```python
llm = ChatOpenAI(
    model="gpt-4o-mini",      # Change model
    temperature=1.0,           # 0.0=deterministic, 1.0=creative
    api_key=api_key
)
```

---

## Troubleshooting

### "scenedetect module not found"
Scene-based mode won't work. Install it:
```bash
pip install scenedetect
```

Or skip scene-based mode and use modes 1 or 2.

### "OpenAI API key not found"
Make sure you have a `.env` file with:
```
OPENAI_API=sk-your-api-key-here
```

### LLM selection fails
- Check API quota and rate limits
- Verify internet connectivity
- Try regenerating the selection
- Try a different mode

### Video stitching fails
- Ensure all segments are valid (check start/end times)
- Try with a shorter video
- Check available disk space
- Verify FFMPEG is installed

### Scene detection returns too few/many scenes
Adjust the threshold parameter in `SceneDetection.py`:
```python
# More sensitive detection
scenes = detect_scenes(video_path, threshold=20.0, min_scene_len=2.0)
```

---

## Performance Tips

1. **Use Batch Mode** for processing multiple videos
   ```bash
   python main.py video1.mp4 --auto-approve
   python main.py video2.mp4 --auto-approve
   ```

2. **Pre-process large videos** to smaller chunks
   - Scene detection and transcription are fast
   - LLM processing is the main bottleneck

3. **Scene-based mode** is generally faster than transcript-based
   - Better for time-sensitive operations

4. **Disable subtitles** if not needed
   - Saves processing time

---

## Comparing the Modes

| Feature | Mode 1 (Continuous) | Mode 2 (Transcript) | Mode 3 (Scene) |
|---------|---|---|---|
| **Speed** | ⚡⚡⚡ Fast | ⚡ Slower | ⚡⚡ Medium |
| **Content Coverage** | Single window | Entire video | Entire video |
| **Visual Quality** | Good | Good | Excellent |
| **Dependencies** | Standard | Standard | Requires scenedetect |
| **Best For** | Quick shorts | Educational | Presentations |
| **Complexity** | Simple | Medium | Advanced |
| **Final Length** | ~120s | ~120s | ~120s |

---

## Examples

### Example 1: YouTube Educational Video

```bash
python main.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

→ Select Mode 2 (Multi-Segment Transcript)
→ Approve first selection
→ Add subtitles: y
→ Wait for processing
→ Share result on TikTok/Instagram! 📱

### Example 2: Podcast Recording

```bash
python main.py "podcast_episode_50.mp4"
```

→ Select Mode 3 (Scene-based)
→ Regenerate once if needed
→ Add subtitles: y
→ Process
→ Post with transcript preview

### Example 3: Batch Processing

```bash
for video in videos/*.mp4; do
    python main.py "$video" --auto-approve
done
```

→ All videos automatically processed and uploaded

---

## API Reference

For developers integrating into other tools:

### GetHighlightMultiSegment
```python
from Components.LanguageTasks import GetHighlightMultiSegment

segments = GetHighlightMultiSegment(
    transcription_text,  # str: timestamped transcription
    target_duration=120  # int: target total duration in seconds
)

# Returns: List[Dict[str, float]] or None
# [{'start': 10.5, 'end': 25.0, 'content': '...'}, ...]
```

### GetHighlightMultiSegmentFromScenes
```python
from Components.LanguageTasks import GetHighlightMultiSegmentFromScenes

segments = GetHighlightMultiSegmentFromScenes(
    scene_transcripts,   # List[Dict]: from map_transcript_to_scenes()
    target_duration=120  # int: target total duration in seconds
)

# Returns: List[Dict[str, float]] or None
```

### stitch_video_segments
```python
from Components.Edit import stitch_video_segments

success = stitch_video_segments(
    input_file,           # str: path to video
    segments,             # List[Dict]: [{'start': ..., 'end': ...}, ...]
    output_file           # str: path to save stitched video
)

# Returns: bool
```

---

## Contributing

Found a bug? Have a feature request?

1. Check SCENE_DETECTION_IMPLEMENTATION.md for technical details
2. Review the code in Components/
3. Test your changes with test_scene_detection.py
4. Submit a pull request

---

## License

See LICENSE file for details.

---

**Happy short-making! 🎬**
