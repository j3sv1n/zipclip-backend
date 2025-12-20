# Output Videos Organization

## Changes Made

The application now automatically creates and stores all output videos in an `output_videos` folder for better organization.

### What Changed

1. **Automatic Directory Creation** - The `output_videos` folder is created automatically when you run the application
2. **Centralized Output** - All generated short videos are saved in `output_videos/` instead of the root directory
3. **Updated .gitignore** - The `output_videos/` folder is excluded from git to avoid committing generated videos

### Directory Structure

```
zipclip-backend/
├── main.py
├── Components/
│   ├── LanguageTasks.py
│   ├── SceneDetection.py
│   └── ...
├── output_videos/              ← NEW: All output shorts saved here
│   ├── my-video_a1b2c3d4_short.mp4
│   ├── podcast_ep50_f5g6h7i8_short.mp4
│   └── ...
├── requirements.txt
└── ...
```

### Code Changes

**main.py (lines 17-21):**
```python
# Create output directory if it doesn't exist
output_dir = "output_videos"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created output directory: {output_dir}")
```

**main.py (line 245):**
```python
# Before:
final_output = f"{clean_title}_{session_id}_short.mp4"

# After:
final_output = os.path.join(output_dir, f"{clean_title}_{session_id}_short.mp4")
```

**.gitignore:**
```ignore
# Output videos directory
output_videos/
```

### Usage

No changes needed! Simply run the app as before:

```bash
python main.py video.mp4
```

The output will be automatically saved in:
```
output_videos/video-name_random-id_short.mp4
```

### Benefits

✅ **Cleaner Root Directory** - Keep the project root organized  
✅ **Easy to Find Outputs** - All shorts in one dedicated folder  
✅ **Automatic Cleanup** - Simply delete the `output_videos/` folder to remove all outputs  
✅ **Batch Processing** - All results from multiple runs organized together  
✅ **Version Control** - Output folder is in .gitignore, so generated files won't be committed  

### Examples

```bash
# Run the app
python main.py my-podcast.mp4
# Output: output_videos/my-podcast_a1b2c3d4_short.mp4

# Batch process multiple videos
for video in *.mp4; do
    python main.py "$video" --auto-approve
done
# All outputs in: output_videos/

# View all generated shorts
ls -lh output_videos/
```

---

**Last Updated**: December 20, 2025
