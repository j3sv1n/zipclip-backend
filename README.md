# ZipClip (Backend)

An AI-powered tool for generating engaging YouTube Shorts from longer videos. Utilizes GPT-4o-mini and Whisper to identify highlights, generate subtitles, and format videos for vertical social media platforms.

## Key Features

- Supports YouTube URLs and local video files
- Fast transcription with CUDA-enabled Whisper
- Automatic highlight selection using AI
- Review and approve segments with auto-approve option
- Automatic subtitle generation with custom styling
- Intelligent cropping for faces or screen recordings
- Vertical 9:16 format for Shorts/Reels
- Command-line interface with automation options
- Concurrent processing with unique session IDs
- Clean output with slugified filenames
- REST API mode for integrations

### Advanced Features
- Scene detection for visual boundaries
- Multi-segment extraction and stitching
- Three processing modes: Continuous, Transcript-based, Scene-based
- Seamless transitions between segments
- Full video content analysis

## Processing Modes

| Aspect | Continuous | Transcript Multi | Scene Multi |
|--------|------------|------------------|-------------|
| Speed | Fast | Slower | Medium |
| Segments | 1 | 3-5 | 3-5 |
| Coverage | 120s window | Full video | Full video |
| Use Case | Quick clips | Educational | Presentations |
| Complexity | Simple | Medium | Advanced |

## Installation

### Requirements

- Python 3.10 or higher
- FFmpeg with development libraries
- NVIDIA GPU with CUDA (recommended for speed)
- ImageMagick for subtitle rendering
- OpenAI API key

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/j3sv1n/zipclip-backend.git
   cd zipclip-backend
   ```

2. Install system packages:
   ```bash
   sudo apt install -y ffmpeg libavdevice-dev libavfilter-dev libopus-dev \
     libvpx-dev pkg-config libsrtp2-dev imagemagick
   ```

3. Update ImageMagick policy for subtitles:
   ```bash
   sudo sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml
   ```

4. Set up Python environment:
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate
   ```

5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

6. Configure environment:
   Copy the example and set your OpenAI key:
   ```bash
   cp .env.example .env
   # Add your API key to .env
   ```

## Usage

### Command Line Interface

#### Interactive with YouTube URL
```bash
./run.sh
# Enter URL when prompted
# Select resolution (auto-selects highest after 5s)
```

#### Direct YouTube URL
```bash
./run.sh "https://youtu.be/VIDEO_ID"
```

#### Local Video File
```bash
./run.sh "/path/to/video.mp4"
```

#### Batch Processing
Create `urls.txt` with URLs, one per line:
```bash
# Auto-approve all
xargs -a urls.txt -I{} ./run.sh --auto-approve {}
```

### API Server Mode

Run as a REST API for frontend integration.

#### Start Server
```bash
./run_api.sh
```

Server endpoints:
- Base: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

#### API Configuration
In `.env`:
```env
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
MAX_CONCURRENT_JOBS=3
UPLOAD_MAX_SIZE=500000000
```

#### API Examples

Submit job:
```bash
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://youtu.be/example", "mode": "continuous", "add_subtitles": true}'
```

Check status:
```bash
curl http://localhost:8000/api/status/{job_id}
```

Download result:
```bash
curl http://localhost:8000/api/download/{job_id} -o output.mp4
```

#### Frontend Integration
See API.md for full documentation, including JavaScript examples.

## Workflow Overview

1. Load video from URL or file
2. Choose resolution (auto highest after 5s)
3. Extract audio to WAV
4. Transcribe with Whisper (~30s for 5min video)
5. AI selects engaging segment
6. Approve or regenerate (auto-approve after 15s)
7. Crop selected clip
8. Apply smart cropping (face-centered or motion-tracked)
9. Generate subtitles with styling
10. Merge audio and video
11. Clean up temp files

Output: `{title}_{session-id}_short.mp4`

## Interactive Options

After segment selection:
```
Selected: 68s - 187s (119s)
Options: [Enter/y] approve, [r] regenerate, [n] cancel
Auto-approve in 15s...
```

## Customization

### Subtitles
In `Components/Subtitles.py`:
- Font: line 51
- Size: line 47
- Color: line 48
- Outline: lines 49-50

### AI Selection
In `Components/LanguageTasks.py`:
- Prompt: line 29
- Model: line 54
- Temperature: line 55

### Motion Tracking
In `Components/FaceCrop.py`:
- Update rate: line 93
- Smoothing: line 115
- Threshold: line 107

### Face Detection
In `Components/FaceCrop.py`:
- Sensitivity: line 37
- Min size: line 37

### Quality Settings
In `Components/Subtitles.py` and `Components/FaceCrop.py`:
- Bitrate: line 74
- Preset: line 73

## Output Naming

Files: `{slugified-title}_{session-id}_short.mp4`

Example: `my-video-title_a1b2c3d4_short.mp4`

- Slugified: lowercase, hyphens for spaces
- Session ID: 8-char unique code
- Resolution: matches source height

## Running Multiple Instances

```bash
./run.sh "url1" &
./run.sh "url2" &
./run.sh "file3.mp4" &
```

Each gets unique ID and temp files.

## Troubleshooting

### GPU/CUDA Problems
```bash
export LD_LIBRARY_PATH=$(find $(pwd)/venv/lib/python3.10/site-packages/nvidia -name "lib" -type d | paste -sd ":" -)
```
Handled automatically by run.sh.

### Subtitle Issues
Check ImageMagick policy:
```bash
grep 'pattern="@\*"' /etc/ImageMagick-6/policy.xml
# Should show rights="read|write"
```

### Face Detection
- Needs faces in first 30 frames
- Screen recordings use motion tracking
- Low res may reduce accuracy

## License

MIT License

