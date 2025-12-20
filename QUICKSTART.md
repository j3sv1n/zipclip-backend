# 🚀 Quick Start Guide - Scene Detection Features

## Installation (2 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify installation
python test_scene_detection.py
```

✅ All tests should pass!

## First Run (Choose Your Mode)

```bash
# Run with any video
python main.py "your_video.mp4"
```

You'll see:
```
SELECT PROCESSING MODE:
1. Continuous clip (original): Extract one continuous 120s segment
2. Multi-segment (transcript): Extract multiple important segments from transcription
3. Multi-segment (scene-based): Detect scenes and extract important ones

Select mode (1-3, default: 1): _
```

---

## Mode Quick Reference

### 🎬 Mode 1: Continuous (Original - Fastest)
**When to use**: You want quick results, video has one main topic
```
python main.py video.mp4
[Select 1]
→ Creates 120s short from a single time window
→ Takes ~90-130 seconds total
```

### 📚 Mode 2: Multi-Segment Transcript (Most Coverage)
**When to use**: Educational videos, podcast clips, montages
```
python main.py video.mp4
[Select 2]
→ Picks 3-5 important moments from entire video
→ LLM combines them intelligently
→ Takes ~100-160 seconds total
```

### 🎨 Mode 3: Scene-Based (Most Intelligent)
**When to use**: Presentations, talking-head videos, structured content
```
python main.py video.mp4
[Select 3]
→ Detects visual scenes automatically
→ Picks best scenes based on visual + text content
→ Takes ~130-220 seconds total
```

---

## Examples

### Example 1: TikTok from YouTube
```bash
python main.py "https://www.youtube.com/watch?v=xyz..."
# Press 2 (Multi-Segment)
# Press Enter when prompted (approve)
# Choose: y for subtitles
# Get: video-title_short.mp4
```

### Example 2: Instagram Reel from Local File
```bash
python main.py /path/to/podcast.mp4
# Press 3 (Scene-Based)
# Press r if you don't like first selection (regenerate)
# Press Enter (approve final selection)
# Get: podcast_short.mp4
```

### Example 3: Batch Process Multiple Videos
```bash
for video in *.mp4; do
    python main.py "$video" --auto-approve
done
```

---

## Troubleshooting

### Issue: "scenedetect not found"
```bash
# Solution: Install it
pip install scenedetect
```

### Issue: "OPENAI_API key not found"
```bash
# Solution: Create .env file
echo "OPENAI_API=sk-your-key-here" > .env
```

### Issue: Mode 3 detects too many/few scenes
Edit `Components/SceneDetection.py` line ~6:
```python
# Change threshold (lower = more scenes, default=27.0)
scenes = detect_scenes(video_path, threshold=20.0)  # More sensitive
scenes = detect_scenes(video_path, threshold=35.0)  # Less sensitive
```

---

## Output Files

Your final video is saved as:
```
{video-name}_{random-id}_short.mp4
```

Example:
```
my-awesome-video_a1b2c3d4_short.mp4
```

✅ Ready to upload to TikTok/Instagram/YouTube Shorts!

---

## Key Differences Summary

| What | Mode 1 | Mode 2 | Mode 3 |
|------|--------|--------|--------|
| Time | ⚡ ~2 min | ⚡ ~2.5 min | ⚡ ~3 min |
| Segments | 1 | 3-5 | 3-5 |
| Best For | Quick clips | Education | Presentations |
| Setup | None | None | Need scenedetect |

---

## Features by Mode

```
Feature                      Mode 1  Mode 2  Mode 3
─────────────────────────────────────────────────
Analyzes entire video        ✓       ✓       ✓
Finds multiple important parts          ✓       ✓
Detects visual scenes                           ✓
Stitches segments together          ✓       ✓
Interactive approval         ✓       ✓       ✓
Can regenerate              ✓       ✓       ✓
Adds subtitles              ✓       ✓       ✓
Crops to 9:16               ✓       ✓       ✓
Auto subtitle               ✓       ✓       ✓
```

---

## Tips & Tricks

### 💡 Pro Tip 1: Regenerate if Not Perfect
If the selection doesn't look good, press `r` to regenerate:
```
Approve and continue? [Enter/y]: r
Regenerating selection...
```

### 💡 Pro Tip 2: Use Batch Mode for Speed
Skip approval for faster processing:
```bash
python main.py video.mp4 --auto-approve
```

### 💡 Pro Tip 3: Skip Subtitles for Speed
If you don't need subtitles:
```
Do you want to add subtitles? (y/n): n
```

### 💡 Pro Tip 4: Choose Mode by Content
- **Tutorial/Educational** → Mode 2
- **Talk/Presentation** → Mode 3
- **Quick preview** → Mode 1

---

## What Happens Step-by-Step

1. **Download/Load** - Get video file
2. **Extract Audio** - Convert to WAV
3. **Transcribe** - Speech-to-text (Whisper)
4. **Analyze** - LLM finds important parts
5. **Approve** - You decide if happy
6. **Extract** - Get segments from video
7. **Stitch** - Combine segments (if multiple)
8. **Crop** - Make vertical for mobile
9. **Subtitles** - Add captions (optional)
10. **Export** - Save final MP4

---

## Advanced Usage

### Custom Target Duration
Edit line ~180 in main.py:
```python
# Change from 120 to different duration (in seconds)
segments = GetHighlightMultiSegment(TransText, target_duration=90)
```

### Custom Scene Detection Threshold
Edit `Components/SceneDetection.py`:
```python
# Lower = more scenes detected
# Higher = fewer scenes detected
scenes = detect_scenes(Vid, threshold=20.0)  # More sensitive
```

### Use Different LLM
Edit `Components/LanguageTasks.py` line ~60:
```python
model="gpt-4o-mini",  # Change to gpt-4, gpt-3.5-turbo, etc.
```

---

## Common Questions

**Q: Which mode should I use?**
A: Try Mode 2 or 3. If slow, use Mode 1.

**Q: Can I process multiple videos?**
A: Yes! Use the batch example with `--auto-approve`.

**Q: Does it require GPU?**
A: No, but GPU makes transcription 5x faster.

**Q: Can I change subtitle style?**
A: Yes, edit `Components/Subtitles.py`.

**Q: How long are the output videos?**
A: ~60-120 seconds (configurable).

**Q: Does it work offline?**
A: No, needs OpenAI API. Local LLMs coming soon!

---

## Documentation

For more details, see:
- 📖 **USER_GUIDE.md** - Complete user guide
- 🏗️ **ARCHITECTURE_DIAGRAMS.md** - How it works
- 📚 **SCENE_DETECTION_IMPLEMENTATION.md** - Technical details
- 📝 **CHANGELOG.md** - What's new

---

## Support

Something not working?
1. Run: `python test_scene_detection.py`
2. Check `.env` has your OpenAI API key
3. Verify FFmpeg is installed: `ffmpeg -version`
4. Read error messages carefully
5. Try regenerating the selection

---

## Ready? Let's Go! 🎬

```bash
python main.py your_video.mp4
```

Select a mode → Approve → Get amazing short! ✨

---

**Happy short-making! 📱🎥**
