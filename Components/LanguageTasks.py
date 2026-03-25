from pydantic import BaseModel,Field
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPENAI_API")

if not api_key:
    raise ValueError("API key not found. Make sure it is defined in the .env file.")

class JSONResponse(BaseModel):
    """
    The response should strictly follow the following structure: -
     [
        {
        start: "Start time of the clip",
        content: "Highlight Text",
        end: "End Time for the highlighted clip"
        }
     ]
    """
    start: float = Field(description="Start time of the clip")
    content: str= Field(description="Highlight Text")
    end: float = Field(description="End time for the highlighted clip")


class SegmentResponse(BaseModel):
    """
    A single segment with start and end times.
    """
    start: float = Field(description="Start time of the segment in seconds")
    end: float = Field(description="End time of the segment in seconds")
    content: str = Field(description="Brief description of what makes this segment interesting")


class MultiSegmentResponse(BaseModel):
    """
    Response containing multiple segments that together form an engaging short.
    """
    segments: list[SegmentResponse] = Field(description="List of segments to extract and stitch together")
    total_duration: float = Field(description="Total duration of all segments combined in seconds")


class CoherentSegmentResponse(BaseModel):
    """
    A single segment from a specific media file.
    """
    media_index: int = Field(description="Index of the media file in the provided list (0-based)")
    start: float = Field(description="Start time of the segment in seconds")
    end: float = Field(description="End time of the segment in seconds")
    content: str = Field(description="Brief description of what makes this segment interesting")


class CoherentMultiSegmentResponse(BaseModel):
    """
    Response containing multiple segments from different media files that together form a coherent short.
    """
    theme: str = Field(description="The identified common theme or story connecting the media files")
    segments: list[CoherentSegmentResponse] = Field(description="List of segments from different media to stitch together")
    total_duration: float = Field(description="Total duration of all segments combined in seconds")

system = """
The input contains a timestamped transcription of a video.
Select a 2-minute segment from the transcription that contains something interesting, useful, surprising, controversial, or thought-provoking.
The selected text should contain only complete sentences.
Do not cut the sentences in the middle.
The selected text should form a complete thought.
Return a JSON object with the following structure:
## Output 
{{
    start: "Start time of the segment in seconds (number)",
    content: "The transcribed text from the selected segment (clean text only, NO timestamps)",
    end: "End time of the segment in seconds (number)"
}}

## Input
{Transcription}
"""

# User = """
# Example
# """




def GetHighlight(Transcription):
    from langchain_openai import ChatOpenAI
    
    try:
        llm = ChatOpenAI(
            model="gpt-5-nano",  # Much cheaper than gpt-4o
            temperature=1.0,
            api_key = api_key
        )

        from langchain.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system",system),
                ("user",Transcription)
            ]
        )
        chain = prompt |llm.with_structured_output(JSONResponse,method="function_calling")
        
        print("Calling LLM for highlight selection...")
        response = chain.invoke({"Transcription":Transcription})
        
        # Validate response
        if not response:
            print("ERROR: LLM returned empty response")
            return None, None
        
        if not hasattr(response, 'start') or not hasattr(response, 'end'):
            print(f"ERROR: Invalid response structure: {response}")
            return None, None
        
        try:
            Start = float(response.start)
            End = float(response.end)
        except (ValueError, TypeError) as e:
            print(f"ERROR: Could not parse start/end times from response")
            print(f"  response.start: {response.start}")
            print(f"  response.end: {response.end}")
            print(f"  Error: {e}")
            return None, None
        
        # Validate times
        if Start < 0 or End < 0:
            print(f"ERROR: Negative time values - Start: {Start}s, End: {End}s")
            return None, None
        
        if End <= Start:
            print(f"ERROR: Invalid time range - Start: {Start}s, End: {End}s (end must be > start)")
            return None, None
        
        # Log the selected segment
        print(f"\n{'='*60}")
        print(f"SELECTED SEGMENT DETAILS:")
        print(f"Time: {Start}s - {End}s ({End-Start}s duration)")
        print(f"Content: {response.content}")
        print(f"{'='*60}\n")
        
        if Start==End:
            Ask = input("Error - Get Highlights again (y/n) -> ").lower()
            if Ask == "y":
                Start, End = GetHighlight(Transcription)
            return Start, End
        return Start,End
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR IN GetHighlight FUNCTION:")
        print(f"{'='*60}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print(f"\nTranscription length: {len(Transcription)} characters")
        print(f"First 200 chars: {Transcription[:200]}...")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return None, None


def GetHighlightMultiSegment(Transcription, target_duration=120):
    """
    Use LLM to select multiple important segments throughout the video
    that together form an engaging short video.
    
    Args:
        Transcription: Timestamped transcription text
        target_duration: Target total duration in seconds (default 120 for 2-minute short)
    
    Returns:
        List of segment dicts with 'start' and 'end' keys, or None if error
    """
    from langchain_openai import ChatOpenAI
    
    multi_system = f"""
The input contains a timestamped transcription of a video.
Identify 3-5 separate segments from throughout the transcription that together form an engaging and cohesive short video.
Select segments that contain interesting, useful, surprising, controversial, or thought-provoking content.
The segments should complement each other and tell a compelling story together.
Try to achieve a total duration of approximately {target_duration} seconds across all segments combined.
Each segment should contain only complete sentences - do not cut sentences in the middle.

Return a JSON object with the following structure:
{{{{
    "segments": [
        {{{{
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "content": "Brief description of what makes this segment interesting"
        }}}},
        ...
    ],
    "total_duration": <sum of all segment durations in seconds (number)>
}}}}

## Input
{{Transcription}}
"""
    
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=1.0,
            api_key=api_key
        )

        from langchain.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", multi_system),
                ("user", Transcription)
            ]
        )
        chain = prompt | llm.with_structured_output(MultiSegmentResponse, method="function_calling")
        
        print(f"Calling LLM for multi-segment selection (target: {target_duration}s)...")
        response = chain.invoke({"Transcription": Transcription})
        
        # Validate response
        if not response:
            print("ERROR: LLM returned empty response")
            return None
        
        if not hasattr(response, 'segments') or not response.segments:
            print(f"ERROR: Invalid response structure or no segments returned")
            return None
        
        segments = []
        total_duration = 0
        
        print(f"\n{'='*60}")
        print(f"SELECTED {len(response.segments)} SEGMENTS:")
        print(f"{'='*60}")
        
        for i, segment in enumerate(response.segments, 1):
            try:
                start = float(segment.start)
                end = float(segment.end)
                
                # Validate times
                if start < 0 or end < 0:
                    print(f"  Warning: Segment {i} has negative time - skipping")
                    continue
                
                if end <= start:
                    print(f"  Warning: Segment {i} has invalid time range (start >= end) - skipping")
                    continue
                
                duration = end - start
                segments.append({
                    'start': start,
                    'end': end,
                    'content': segment.content
                })
                total_duration += duration
                
                print(f"  Segment {i}: {start:.2f}s - {end:.2f}s ({duration:.2f}s)")
                print(f"    Content: {segment.content}")
                
            except (ValueError, TypeError) as e:
                print(f"  Warning: Could not parse segment {i}: {e}")
                continue
        
        print(f"\nTotal duration: {total_duration:.2f}s")
        print(f"{'='*60}\n")
        
        if not segments:
            print("ERROR: No valid segments extracted from LLM response")
            return None
        
        return segments
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR IN GetHighlightMultiSegment FUNCTION:")
        print(f"{'='*60}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print(f"\nTranscription length: {len(Transcription)} characters")
        print(f"First 200 chars: {Transcription[:200]}...")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return None


def GetHighlightMultiSegmentFromScenes(scene_transcripts, target_duration=120):
    """
    Use LLM to select the most important scenes from detected scene boundaries.
    
    Args:
        scene_transcripts: List of scene dicts from map_transcript_to_scenes with keys:
                          'scene_start', 'scene_end', 'duration', 'transcript'
        target_duration: Target total duration in seconds (default 120 for 2-minute short)
    
    Returns:
        List of segment dicts with 'start' and 'end' keys, or None if error
    """
    from langchain_openai import ChatOpenAI
    
    # Build scene summary
    scene_summary = "DETECTED SCENES WITH TRANSCRIPTS:\n"
    scene_summary += "=" * 80 + "\n\n"
    
    for i, scene in enumerate(scene_transcripts, 1):
        scene_summary += (
            f"Scene {i}: {scene['scene_start']:.2f}s - {scene['scene_end']:.2f}s "
            f"(duration: {scene['duration']:.2f}s)\n"
        )
        scene_summary += f"Transcript: {scene['transcript']}\n"
        scene_summary += "-" * 80 + "\n\n"
    
    scene_system = f"""
You are analyzing a video that has been split into detected scenes with associated transcripts.
Your task is to select 3-5 important scenes that together form an engaging and cohesive short video.
Choose scenes that contain interesting, useful, surprising, controversial, or thought-provoking content.
The selected scenes should complement each other and tell a compelling story.
Try to achieve a total duration of approximately {target_duration} seconds.

Analyze the scene boundaries and transcripts, then select whole scenes (don't split them).
Return a JSON object with the following structure:
{{{{
    "segments": [
        {{{{
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "content": "Why this scene is important"
        }}}},
        ...
    ],
    "total_duration": <sum of all scene durations in seconds (number)>
}}}}

## Scene Information
{scene_summary}
"""
    
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=1.0,
            api_key=api_key
        )

        from langchain.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", scene_system),
                ("user", "Please select the most important scenes for the short video.")
            ]
        )
        chain = prompt | llm.with_structured_output(MultiSegmentResponse, method="function_calling")
        
        print(f"Calling LLM for scene-based selection (target: {target_duration}s)...")
        response = chain.invoke({})
        
        # Validate response
        if not response:
            print("ERROR: LLM returned empty response")
            return None
        
        if not hasattr(response, 'segments') or not response.segments:
            print(f"ERROR: Invalid response structure or no segments returned")
            return None
        
        segments = []
        total_duration = 0
        
        print(f"\n{'='*60}")
        print(f"SELECTED {len(response.segments)} SCENES:")
        print(f"{'='*60}")
        
        for i, segment in enumerate(response.segments, 1):
            try:
                start = float(segment.start)
                end = float(segment.end)
                
                # Validate times
                if start < 0 or end < 0:
                    print(f"  Warning: Segment {i} has negative time - skipping")
                    continue
                
                if end <= start:
                    print(f"  Warning: Segment {i} has invalid time range (start >= end) - skipping")
                    continue
                
                duration = end - start
                segments.append({
                    'start': start,
                    'end': end,
                    'content': segment.content
                })
                total_duration += duration
                
                print(f"  Scene {i}: {start:.2f}s - {end:.2f}s ({duration:.2f}s)")
                print(f"    Reason: {segment.content}")
                
            except (ValueError, TypeError) as e:
                print(f"  Warning: Could not parse segment {i}: {e}")
                continue
        
        print(f"\nTotal duration: {total_duration:.2f}s")
        print(f"{'='*60}\n")
        
        if not segments:
            print("ERROR: No valid segments extracted from LLM response")
            return None
        
        return segments
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR IN GetHighlightMultiSegmentFromScenes FUNCTION:")
        print(f"{'='*60}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print(f"Number of scenes: {len(scene_transcripts)}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return None


def GetHighlightMultiSegmentFromFrames(scene_segments, target_duration=120):
    """
    Use LLM to select important scenes based on visual analysis of what's in each scene.
    
    Args:
        scene_segments: List of scene dicts with keys:
                       'scene_start', 'scene_end', 'duration', 'frame_description'
        target_duration: Target total duration in seconds (default 120 for 2-minute short)
    
    Returns:
        List of segment dicts with 'start' and 'end' keys, or None if error
    """
    from langchain_openai import ChatOpenAI
    
    # Build scene summary with visual analysis
    scene_summary = "DETECTED SCENES WITH VISUAL ANALYSIS:\n"
    scene_summary += "=" * 80 + "\n\n"
    
    for i, scene in enumerate(scene_segments, 1):
        scene_summary += (
            f"Scene {i}: {scene['scene_start']:.2f}s - {scene['scene_end']:.2f}s "
            f"(duration: {scene['duration']:.2f}s)\n"
        )
        scene_summary += f"Visual content: {scene['frame_description']}\n"
        scene_summary += "-" * 80 + "\n\n"
    
    min_duration = max(60, int(target_duration * 0.6))  # At least 60s or 60% of target
    
    scene_system = f"""
You are analyzing a video and selecting the most important and memorable scenes based on their visual content.
Each scene has been analyzed to describe what's happening visually (people, activities, emotions, settings).

Your task is to select scenes that together create a compelling short video.

DURATION REQUIREMENTS:
- MAXIMUM 10 seconds per segment (strict limit)
- Exception: Only use up to 20s if the moment is EXTREMELY important (e.g., main subject/couple interaction)
- MINIMUM total duration: {min_duration} seconds
- TARGET total duration: {target_duration} seconds
- You MUST select enough scenes to reach at least {min_duration}s

Selection criteria (based on visual content):
- Prioritize scenes with key people/moments (e.g., main subjects/couple, important interactions)
- Include emotional or significant moments
- Include celebratory or joyful moments
- Select scenes that capture the essence/highlights of the event
- Distribute selections throughout the video
- Aim for 6-12+ scenes total (more shorter clips for better pacing)

IMPORTANT: For each segment, select ONLY the duration you need from the scene:
- If scene is 30s long but only the first 10s shows the important moment, use start to (start+10)
- You can split a long scene into multiple clips if different parts are important
- Default to 10s per clip unless it's essential to go longer

Select segments using exact start and end times. You can break up long scenes into multiple clips.

Return a JSON object with the following structure:
{{{{
    "segments": [
        {{{{
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "content": "Why this segment is important/memorable"
        }}}},
        ...
    ],
    "total_duration": <sum of all segment durations in seconds (number)>
}}}}

## Scene Information
{scene_summary}
"""
    
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=1.0,
            api_key=api_key
        )

        from langchain.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", scene_system),
                ("user", f"Create a {target_duration}s video (minimum {min_duration}s). Use 10s max per clip normally. Only go to 20s if absolutely critical. Select/split scenes as needed to meet duration while keeping clips short and punchy.")
            ]
        )
        chain = prompt | llm.with_structured_output(MultiSegmentResponse, method="function_calling")
        
        print(f"Calling LLM for scene selection based on visual content...")
        print(f"Target: {target_duration}s, Minimum: {min_duration}s")
        print(f"Max per segment: 10s (20s only for critical moments)")
        response = chain.invoke({})
        
        # Validate response
        if not response:
            print("ERROR: LLM returned empty response")
            return None
        
        if not hasattr(response, 'segments') or not response.segments:
            print(f"ERROR: Invalid response structure or no segments returned")
            return None
        
        segments = []
        total_duration = 0
        
        print(f"\n{'='*60}")
        print(f"SELECTED {len(response.segments)} SEGMENTS:")
        print(f"{'='*60}")
        
        for i, segment in enumerate(response.segments, 1):
            try:
                start = float(segment.start)
                end = float(segment.end)
                
                # Validate times
                if start < 0 or end < 0:
                    print(f"  Warning: Segment {i} has negative time - skipping")
                    continue
                
                if end <= start:
                    print(f"  Warning: Segment {i} has invalid time range (start >= end) - skipping")
                    continue
                
                duration = end - start
                
                # Enforce max duration (10s normally, 20s for critical)
                # Give LLM some flexibility but warn if exceeded
                if duration > 20:
                    print(f"  Warning: Segment {i} is {duration:.1f}s (exceeds 20s max) - truncating to 20s")
                    end = start + 20
                    duration = 20
                elif duration > 10:
                    print(f"  Note: Segment {i} is {duration:.1f}s (above 10s standard, but acceptable)")
                
                segments.append({
                    'start': start,
                    'end': end,
                    'content': segment.content
                })
                total_duration += duration
                
                print(f"  Segment {i}: {start:.2f}s - {end:.2f}s ({duration:.2f}s)")
                print(f"    Reason: {segment.content}")
                
            except (ValueError, TypeError) as e:
                print(f"  Warning: Could not parse segment {i}: {e}")
                continue
        
        print(f"\nTotal duration: {total_duration:.2f}s (target: {target_duration}s, minimum: {min_duration}s)")
        
        # If total duration is below minimum, warn user
        if total_duration < min_duration:
            print(f"⚠️  WARNING: Total duration {total_duration:.2f}s is below minimum {min_duration}s")
            print(f"    Consider selecting more or longer scenes")
        
        print(f"{'='*60}\n")
        
        if not segments:
            print("ERROR: No valid segments extracted from LLM response")
            return None
        
        return segments
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR IN GetHighlightMultiSegmentFromFrames FUNCTION:")
        print(f"{'='*60}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print(f"Number of scenes: {len(scene_segments)}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return None


def GetCoherentHighlights(media_metadata_list, target_duration=120):
    """
    Identify connections between multiple media files and select segments 
    that together form a coherent short video.
    
    Args:
        media_metadata_list: List of dicts with:
                            'index': int,
                            'type': 'video' or 'image',
                            'filename': str,
                            'duration': float,
                            'transcript': str (for videos),
                            'visual_description': str
        target_duration: Target total duration in seconds
    
    Returns:
        List of segment dicts with 'media_index', 'start', 'end', or None if error
    """
    from langchain_openai import ChatOpenAI
    
    media_summary = "INPUT MEDIA FILES:\n"
    media_summary += "=" * 80 + "\n\n"
    
    for item in media_metadata_list:
        file_idx_str = f" (Original File Index: {item.get('file_index', 'N/A')})"
        media_summary += (
            f"Media {item['index']} ({item['type']}){file_idx_str}: {item['filename']}\n"
            f"Duration: {item['duration']:.2f}s\n"
        )
        if item['type'] == 'video' and item.get('transcript'):
            media_summary += f"Transcript: {item['transcript'][:500]}...\n"
        media_summary += f"Visual Context: {item['visual_description']}\n"
        media_summary += "-" * 80 + "\n\n"
    
    coherent_system = f"""
You are a creative video editor. You have been given a collection of media clips (video scenes and images).
Your task is to:
1. Identify a common theme, story, or "vibe" that connects these files together.
2. Select segments from these different media items to create a coherent, intelligent, and engaging short video.
3. CRITICAL: Items with the same 'Original File Index' come from the same original uploaded file (e.g., different scenes from one video). You MUST include at least one segment from EVERY SINGLE unique 'Original File Index' provided. You do not need to use every item/scene, but every original file must be represented.
4. CRITICAL ORDERING: Do NOT simply output the segments in the sequential order they were provided. You must non-linearly reorder and interleave them to create a compelling, creative narrative or montage.
5. FILTERING: Filter out unwanted elements like screen recording UI menus, scrolling contact lists, or irrelevant filler, focusing only on the important visual and narrative aspects.
6. For images, you can assume they will be shown for 3-5 seconds (they have a fixed duration in the input).
7. For videos, select punchy segments (5-15s typically).
8. The final result should feel like a single, well-paced story featuring ALL provided media files.

DURATION REQUIREMENTS:
- TARGET total duration: {target_duration} seconds.
- Each segment should be meaningful and follow the identified theme.

Return a JSON object with the following structure:
{{{{
    "theme": "Description of the identified theme",
    "segments": [
        {{{{
            "media_index": <index of the media file (number)>,
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "content": "Why this segment fits the theme"
        }}}},
        ...
    ],
    "total_duration": <sum of all segment durations in seconds (number)>
}}}}

## Media Information
{media_summary}
"""
    
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=1.0,
            api_key=api_key
        )

        from langchain.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", coherent_system),
                ("user", f"Find the best connection between these {len(media_metadata_list)} files and create a {target_duration}s coherent short.")
            ]
        )
        chain = prompt | llm.with_structured_output(CoherentMultiSegmentResponse, method="function_calling")
        
        print(f"Calling LLM for coherent multi-media selection...")
        response = chain.invoke({})
        
        # Validate response
        if not response:
            print("ERROR: LLM returned empty response")
            return None
        
        if not hasattr(response, 'segments') or not response.segments:
            print(f"ERROR: No segments returned")
            return None
        
        segments = []
        print(f"\n{'='*60}")
        print(f"IDENTIFIED THEME: {response.theme}")
        print(f"SELECTED {len(response.segments)} SEGMENTS:")
        print(f"{'='*60}")
        
        for i, segment in enumerate(response.segments, 1):
            try:
                segments.append({
                    'media_index': int(segment.media_index),
                    'start': float(segment.start),
                    'end': float(segment.end),
                    'content': segment.content
                })
                print(f"  Segment {i}: Media {segment.media_index} | {segment.start:.2f}s - {segment.end:.2f}s")
                print(f"    Reason: {segment.content}")
            except Exception as e:
                print(f"  Warning: Skipping invalid segment {i}: {e}")
        
        print(f"Total duration: {response.total_duration:.2f}s")
        print(f"{'='*60}\n")
        
        return {
            "theme": response.theme,
            "segments": segments
        }
        
    except Exception as e:
        print(f"ERROR IN GetCoherentHighlights: {e}")
        import traceback
        traceback.print_exc()
        return None


def GetMusicMood(theme, media_metadata_list):
    """
    Suggest a music genre and mood based on the theme and media content.
    """
    from langchain_openai import ChatOpenAI
    
    media_info = ""
    for item in media_metadata_list[:3]: # Just a sample
        media_info += f"- {item['type']}: {item['visual_description'][:100]}\n"
        
    mood_system = """
You are a video producer. Based on the theme of a video and descriptions of its content, 
suggest a background music genre and mood.
Return a simple string like "Upbeat, energetic electronic" or "Calm, reflective piano".

Theme: {theme}
Media Sample:
{media_info}
"""
    
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=api_key
        )
        
        from langchain.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([("system", mood_system)])
        chain = prompt | llm
        
        print(f"Calling LLM for music mood selection...")
        response = chain.invoke({"theme": theme, "media_info": media_info})
        mood = response.content if hasattr(response, 'content') else str(response)
        
        return mood.strip()
    except Exception as e:
        print(f"Error in GetMusicMood: {e}")
        return "Inspiring, corporate background"


if __name__ == "__main__":
    print(GetHighlight(User))
