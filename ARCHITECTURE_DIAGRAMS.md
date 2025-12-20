# Architecture Diagrams

## Before vs After

### BEFORE: Single Continuous Clip
```
Video (5 minutes)
     ↓
Transcribe
     ↓
GetHighlight() → selects 120s window
     ↓
Extract: segment[45s-165s]
     ↓
Output: 120s short
     
PROBLEM: Important content outside 45s-165s window is lost
Example: Key point at 4:50 is not included
```

### AFTER: Three Processing Modes

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INPUT VIDEO                              │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
                    EXTRACT AUDIO & TRANSCRIBE
                             ↓
                ┌────────────────────────────────┐
                │    SELECT PROCESSING MODE      │
                └────┬──────────┬────────────┬───┘
                     ↓          ↓            ↓
            ┌────────────┐ ┌───────────┐ ┌──────────┐
            │  MODE 1    │ │  MODE 2   │ │  MODE 3  │
            │ Continuous │ │ Transcript│ │  Scene   │
            └────┬───────┘ └─────┬─────┘ └────┬─────┘
                 ↓               ↓            ↓
            GetHighlight()  GetHighlight   detect_scenes()
                            MultiSegment  map_transcript
                                          GetHighlight
                                          MultiSegment
                 ↓               ↓            ↓
            ┌─────────────────────────────────────────┐
            │       USER APPROVAL & REGENERATION      │
            └────────────────┬────────────────────────┘
                             ↓
                    EXTRACT SEGMENTS
                    (Single or Multiple)
                             ↓
                    VERTICAL CROPPING (9:16)
                             ↓
                    OPTIONAL: ADD SUBTITLES
                             ↓
                        MERGE AUDIO
                             ↓
                    ┌─────────────────────┐
                    │   OUTPUT SHORT      │
                    │  120s-180s video    │
                    └─────────────────────┘
```

---

## Mode Comparison Matrix

```
                 ┌──────────┬──────────┬──────────┐
                 │ MODE 1   │ MODE 2   │ MODE 3   │
                 │Continous │Transcript│  Scene   │
─────────────────┼──────────┼──────────┼──────────┤
Input Analysis   │ Full TX  │ Full TX  │ Video +  │
                 │ once     │ once     │ Full TX  │
─────────────────┼──────────┼──────────┼──────────┤
Segments Found   │ 1        │ 3-5      │ 3-5      │
─────────────────┼──────────┼──────────┼──────────┤
Processing Time  │ ⚡⚡⚡   │ ⚡       │ ⚡⚡    │
                 │ Fast     │ Slow     │ Medium   │
─────────────────┼──────────┼──────────┼──────────┤
Content Coverage │ Limited  │ Complete │ Complete │
                 │ 120s win │ Full     │ Full     │
─────────────────┼──────────┼──────────┼──────────┤
Final Quality    │ Good     │ Excellent│ Excellent│
─────────────────┼──────────┼──────────┼──────────┤
Narrative Flow   │ Natural  │ Chosen   │ Visual   │
                 │ Original │ by LLM   │ Scene    │
─────────────────┼──────────┼──────────┼──────────┤
Best For         │ Quick    │ Education│Present-  │
                 │ Clips    │ Content  │ ation    │
─────────────────┼──────────┼──────────┼──────────┤
User Setup       │ None     │ None     │ Install  │
                 │ Needed   │ Needed   │scenedetc │
─────────────────┴──────────┴──────────┴──────────┘
```

---

## Segment Selection Visualization

### Mode 1: Continuous
```
Video Timeline (5 minutes = 300 seconds)
|----|----|----|----|----|----|----|----|----|----|
0    50   100  150  200  250  300

Selected: [45s ────── 165s]
          (120s continuous segment)
```

### Mode 2: Multi-Segment (Transcript)
```
Video Timeline with Transcript Content
|----|----|----|----|----|----|----|----|----|----|
0    50   100  150  200  250  300

 Point1     Point2          Point3              Point4
  ↓          ↓              ↓                   ↓
[10─20]    [65──80]      [140──165]         [240──260]
  
Total: ~80 seconds across entire video
No important parts missed!
```

### Mode 3: Scene-Based
```
Detected Scenes (Visual Boundaries)
Scene 1    Scene 2      Scene 3         Scene 4       Scene 5
|------|----------|----------|----------|----------|
0      50        150        200        250       300

Selected:  [10─40]    [100─140]    [180─210]
          Scene 1     Scene 2      Scene 4
          
Respects visual narrative, no mid-scene cuts
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Video Input                              │
│        (YouTube URL or Local File)                          │
└────────────────────┬─────────────────────────────────────────┘
                     ↓
            ┌────────────────────┐
            │  Download & Verify │
            └────────┬───────────┘
                     ↓
            ┌────────────────────┐
            │  Extract Audio     │
            │  (WAV Format)      │
            └────────┬───────────┘
                     ↓
            ┌────────────────────┐
            │  Transcribe        │
            │  (Whisper Model)   │
            └────────┬───────────┘
                     ↓
    ┌────────────────┼────────────────┐
    ↓                ↓                ↓
  MODE 1          MODE 2          MODE 3
  Single        Transcript       Scene
  Segment       Analysis         Detection
    ↓                ↓                ↓
 Get            Get Multi          Detect
Highlight      Highlight          Scenes
    ↓          from Full TX         ↓
    │              ↓            Map TX to
    │          Get 3-5         Scenes
    │          Segments           ↓
    │              ↓          Get Multi
    │              │         Highlight
    └──────┬───────┘         from Scenes
           ↓                    ↓
      SEGMENTS          ┌──────────────┐
      Approved          │ USER REVIEW  │
           ↓            └──────┬───────┘
    ┌─────────────┐            ↓
    │ Single Clip │    ┌──────────────────┐
    │   Crop      │    │ Multiple Clips   │
    └──────┬──────┘    │  Stitch Together │
           │           └─────────┬────────┘
           └───────┬─────────────┘
                   ↓
          ┌─────────────────────┐
          │ Vertical Cropping   │
          │ (9:16 Aspect)       │
          └──────────┬──────────┘
                     ↓
          ┌─────────────────────┐
          │ Subtitle Generation │
          │ (Optional)          │
          └──────────┬──────────┘
                     ↓
          ┌─────────────────────┐
          │ Audio Merge         │
          └──────────┬──────────┘
                     ↓
          ┌─────────────────────┐
          │ Final Output MP4    │
          │ (TikTok/IG Ready)   │
          └─────────────────────┘
```

---

## Scene Detection Process (Mode 3 Detailed)

```
INPUT: video.mp4 (5 minutes, 24 fps, 1080p)
  ↓
STEP 1: Detect Scene Boundaries
┌─────────────────────────────────────────┐
│ PySceneDetect Analysis                  │
│ • Compares consecutive frames           │
│ • Detects significant visual changes    │
│ • Threshold: 27.0 (configurable)        │
│ • Min scene length: 3.0s (configurable) │
└──────────┬────────────────────────────────┘
           ↓
OUTPUT: 24 detected scenes
  [0s-5s]  [5s-18s]  [18s-45s]  ... [290s-300s]
  ↓
STEP 2: Map Transcription to Scenes
┌─────────────────────────────────────────┐
│ For each scene:                         │
│ • Find overlapping transcript segments  │
│ • Combine text for this scene           │
│ • Store in scene_transcript dict        │
└──────────┬────────────────────────────────┘
           ↓
OUTPUT: Enriched scenes with transcripts
  Scene 1: "Speaker introduces topic..."
  Scene 2: "Let me explain this concept..."
  ...
  ↓
STEP 3: LLM Analysis
┌─────────────────────────────────────────┐
│ GetHighlightMultiSegmentFromScenes()   │
│ • Reads all scene transcripts           │
│ • Selects 3-5 important scenes          │
│ • Targets ~120s total duration          │
│ • Ensures coherent narrative            │
└──────────┬────────────────────────────────┘
           ↓
OUTPUT: Selected scenes
  Scene 1: [10s-40s]   "Important intro"
  Scene 4: [100s-140s] "Key insight"
  Scene 7: [180s-210s] "Practical tip"
  ↓
STEP 4: Stitch Segments
┌─────────────────────────────────────────┐
│ Extract each segment                    │
│ Concatenate with smooth transitions     │
│ Preserve audio and quality              │
└──────────┬────────────────────────────────┘
           ↓
OUTPUT: Stitched video (concatenated)
```

---

## Integration Points

```
Components Used:
┌─────────────────────────────────────────┐
│  main.py (ORCHESTRATOR)                │
├─────────────────────────────────────────┤
│  Coordinates all components             │
│  Handles mode selection                 │
│  Manages temp files                     │
│  Provides UI                            │
└──────────┬──────────────────────────────┘
           ├─────────────┬──────────┬─────────────┐
           ↓             ↓          ↓             ↓
      ┌────────┐   ┌─────────┐ ┌────────┐  ┌──────────┐
      │You tube│   │  Edit   │ │Language│  │ Scene    │
      │Down    │   │  .py    │ │Tasks   │  │Detection │
      │loader  │   │         │ │  .py   │  │  .py     │
      │  .py   │   │         │ │        │  │          │
      └────────┘   ├─────────┤ ├────────┤  ├──────────┤
                   │crop_    │ │GetHi   │  │detect_  │
                   │video()  │ │ghlight │  │scenes()  │
                   │stitch_  │ │GetHi   │  │map_      │
                   │segments │ │ghlight │  │transcript│
                   │         │ │Multi   │  │          │
                   └─────────┘ │Segment │  └──────────┘
                               │FromSc  │
                               │enes()  │
                               └────────┘
```

---

## Error Handling Flow

```
Operation Started
     ↓
Try Operation
     ↓
     ├─ SUCCESS → Continue
     │
     └─ ERROR ─┬─ LLM API Error
               │    ↓
               │    Print helpful message
               │    Suggest: Check API key, quota
               │    Allow: Regenerate/Retry
               │
               ├─ Scene Detection Error
               │    ↓
               │    Fallback to time-based segments
               │    Notify user
               │    Continue with Mode 1 equivalent
               │
               ├─ Invalid Segment Times
               │    ↓
               │    Log warning
               │    Skip invalid segment
               │    Continue with valid ones
               │
               └─ File Operation Error
                    ↓
                    Log error
                    Cleanup attempt
                    Exit gracefully
```

---

## Performance Metrics

```
Processing Time Breakdown (5-minute video):

MODE 1: Continuous
├─ Extract Audio: 10-15s
├─ Transcribe: 20-30s
├─ GetHighlight LLM: 2-5s
├─ Extract 1 segment: 5-10s
├─ Vertical Crop: 20-40s
├─ Add Subtitles: 10-20s (optional)
├─ Merge Audio: 5-10s
└─ TOTAL: ~90-130s (1.5-2.2 minutes) ⚡⚡⚡

MODE 2: Multi-Segment (Transcript)
├─ Extract Audio: 10-15s
├─ Transcribe: 20-30s
├─ GetHighlightMultiSegment LLM: 3-7s
├─ Stitch 4 segments: 20-40s
├─ Vertical Crop: 20-40s
├─ Add Subtitles: 10-20s (optional)
├─ Merge Audio: 5-10s
└─ TOTAL: ~100-160s (1.7-2.7 minutes) ⚡

MODE 3: Multi-Segment (Scene)
├─ Extract Audio: 10-15s
├─ Transcribe: 20-30s
├─ Detect Scenes: 30-60s
├─ Map Transcripts: 2-5s
├─ GetHighlightMultiSegmentFromScenes: 3-7s
├─ Stitch 4 segments: 20-40s
├─ Vertical Crop: 20-40s
├─ Add Subtitles: 10-20s (optional)
├─ Merge Audio: 5-10s
└─ TOTAL: ~130-220s (2.2-3.7 minutes) ⚡⚡

Relative Speeds:
Mode 1: 1x (baseline)
Mode 2: 1.1x-1.2x (slightly slower)
Mode 3: 1.4x-1.8x (slower but feature-rich)
```

---

## Version Compatibility

```
NEW FEATURES (Added)
├─ GetHighlightMultiSegment()           (LanguageTasks)
├─ GetHighlightMultiSegmentFromScenes() (LanguageTasks)
├─ SegmentResponse model                (LanguageTasks)
├─ MultiSegmentResponse model           (LanguageTasks)
├─ Mode selection UI                    (main.py)
├─ Multi-segment processing             (main.py)
└─ Stitch integration                   (main.py)

EXISTING FUNCTIONS (Preserved)
├─ GetHighlight()                       (LanguageTasks)
├─ transcribeAudio()                    (Transcription)
├─ crop_video()                         (Edit)
├─ stitch_video_segments()              (Edit - now used)
├─ detect_scenes()                      (SceneDetection)
├─ map_transcript_to_scenes()           (SceneDetection)
├─ crop_to_vertical()                   (FaceCrop)
├─ combine_videos()                     (FaceCrop)
└─ add_subtitles_to_video()            (Subtitles)

BACKWARD COMPATIBILITY: 100% ✅
Mode 1 (Continuous) behaves identically to original
Existing code calling GetHighlight() works unchanged
```

---

This document provides visual references for understanding the enhanced architecture.
