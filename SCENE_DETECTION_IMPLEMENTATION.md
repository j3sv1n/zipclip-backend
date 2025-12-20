# Scene Detection & Multi-Segment Implementation

## Overview

The ZipClip backend has been enhanced to support three different modes for creating shorts:

1. **Continuous Clip Mode (Original)** - Extracts a single continuous 120-second segment
2. **Multi-Segment Mode (Transcript-based)** - Analyzes the entire transcription and selects multiple important segments throughout the video
3. **Multi-Segment Mode (Scene-based)** - Detects visual scenes in the video and selects the most important ones

## Architecture Changes

### 1. New Functions in `Components/LanguageTasks.py`

#### `GetHighlightMultiSegment(Transcription, target_duration=120)`
- Analyzes the full transcription to identify multiple important segments
- Uses the `MultiSegmentResponse` model to structure the LLM output
- Returns a list of segments with start/end times
- Attempts to reach the target duration (120s default) while selecting coherent content

#### `GetHighlightMultiSegmentFromScenes(scene_transcripts, target_duration=120)`
- Works with pre-detected scene boundaries from `SceneDetection.py`
- Analyzes scenes rather than continuous transcript
- Selects whole scenes (no splitting within scene boundaries)
- Better for visual content where natural scene breaks exist

### 2. Enhanced `main.py` Workflow

#### Mode Selection
Users are now prompted to choose their processing mode:
```
SELECT PROCESSING MODE:
1. Continuous clip (original): Extract one continuous 120s segment
2. Multi-segment (transcript): Extract multiple important segments from transcription
3. Multi-segment (scene-based): Detect scenes and extract important ones
```

#### Processing Flow
1. **Download/Load Video** → Extract Audio → Transcribe
2. **Route to Selected Mode**:
   - **Mode 1**: Use `GetHighlight()` (original function)
   - **Mode 2**: Use `GetHighlightMultiSegment()`
   - **Mode 3**: Run `detect_scenes()` → `map_transcript_to_scenes()` → `GetHighlightMultiSegmentFromScenes()`
3. **User Approval**: Interactive confirmation loop with regeneration option
4. **Video Processing**:
   - Single segment: Use `crop_video()` as before
   - Multiple segments: Use `stitch_video_segments()` to combine them
5. **Post-processing**: Apply vertical cropping, subtitles, and audio

### 3. Scene Detection Integration

Uses the existing `Components/SceneDetection.py` which provides:
- `detect_scenes(video_path, threshold=27.0, min_scene_len=3.0)` - Detects scene boundaries
- `map_transcript_to_scenes(scenes, transcriptions)` - Associates transcription with scenes

## Key Improvements

### 1. Content Coverage
- **Before**: Limited to a single 120-second window, may miss important content elsewhere
- **After**: Can pull engaging moments from throughout the entire video

### 2. Narrative Quality
- **Scenes**: Respects visual narrative structure by using detected scene boundaries
- **Transcript-based**: Creates a coherent narrative by LLM selection

### 3. Flexibility
- Users can choose the method that works best for their content
- Easy to extend with additional modes (e.g., speaker-based, topic-based)

## Usage Examples

### Example 1: Continuous Mode (Original)
```bash
python main.py "path/to/video.mp4"
# Select mode 1 when prompted
# Select clip as before
```

### Example 2: Multi-Segment Transcript Mode
```bash
python main.py "path/to/video.mp4"
# Select mode 2 when prompted
# LLM will select 3-5 important segments from entire video
# Approve or regenerate
```

### Example 3: Scene-Based Mode
```bash
python main.py "path/to/video.mp4"
# Select mode 3 when prompted
# Scenes are detected first, then important ones are selected
# More suitable for talking-head or presentation videos
```

### Batch Processing
```bash
python main.py "path/to/video.mp4" --auto-approve
# Auto-approves selections without user interaction
```

## Technical Details

### Multi-Segment Processing
The `stitch_video_segments()` function in `Components/Edit.py`:
- Validates all segment time ranges
- Extracts each segment as a video clip
- Concatenates clips using MoviePy's `concatenate_videoclips()`
- Handles audio merging and codec settings

### Subtitle Integration
For multi-segment videos:
- Subtitles are generated based on the transcription
- The start time of the first segment is used as reference
- All relevant transcription segments are included

### Temporary Files
Each run uses a session ID to avoid conflicts:
- `audio_{session_id}.wav`
- `temp_clip_{session_id}.mp4`
- `temp_cropped_{session_id}.mp4`
- `temp_subtitled_{session_id}.mp4`
- `temp_stitched_{session_id}.mp4` (for multi-segment mode)

## Error Handling

All modes include comprehensive error handling:
- LLM API failures → Exits gracefully with error messages
- Scene detection failures → Falls back to time-based segments
- Invalid segment times → Skips problematic segments and warns user
- Missing dependencies → Provides helpful error messages

## Dependencies

The implementation uses existing dependencies:
- `scenedetect` - Scene detection (already in requirements.txt)
- `moviepy` - Video processing
- `langchain` - LLM integration
- `pydantic` - Data validation

## Future Enhancements

Potential improvements:
1. **Keyword-based selection** - Extract segments mentioning specific topics
2. **Speaker detection** - Select segments with different speakers
3. **Emotion detection** - Extract emotionally engaging moments
4. **Music-based segmentation** - Use audio analysis for better boundaries
5. **Custom duration targets** - Allow users to specify exact output length
6. **Segment quality scoring** - Rate segments and rank by interest level

## Migration Notes

- The original continuous mode is still available as Mode 1
- Existing scripts calling `GetHighlight()` will continue to work
- No breaking changes to existing APIs
- Scene detection is optional - not required for running the app
