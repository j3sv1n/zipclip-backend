from pydantic import BaseModel,Field
from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv()

api_key = os.getenv("OPENAI_API")

if not api_key:
    raise ValueError("API key not found. Make sure it is defined in the .env file.")


MIN_DURATION_TOLERANCE_SECONDS = 2
MAX_DURATION_TOLERANCE_SECONDS = 6
MAX_DURATION_PLANNING_ATTEMPTS = 2

class JSONResponse(BaseModel):
    """
    The response should strictly follow the following structure:
    """
    reasoning: str = Field(description="Think step-by-step about why this segment is highly engaging, has a strong hook, and a satisfying conclusion.", default="")
    start: float = Field(description="Start time of the clip")
    content: str= Field(description="Highlight Text")
    end: float = Field(description="End time for the highlighted clip")


class SegmentResponse(BaseModel):
    """
    A single segment with start and end times.
    """
    start: float = Field(description="Start time of the segment in seconds")
    end: float = Field(description="End time of the segment in seconds")
    role: str = Field(description="Narrative role (e.g., Hook, Build-up, Climax, Resolution)", default="Content")
    content: str = Field(description="Brief description of what makes this segment interesting")


class MultiSegmentResponse(BaseModel):
    """
    Response containing multiple segments that together form an engaging short.
    """
    story_arc_explanation: str = Field(description="Step-by-step reasoning of how these segments create a cohesive story arc with a strong hook and satisfying resolution.", default="")
    segments: list[SegmentResponse] = Field(description="List of segments to extract and stitch together")
    total_duration: float = Field(description="Total duration of all segments combined in seconds")


class CoherentSegmentResponse(BaseModel):
    """
    A single segment from a specific media file.
    """
    media_index: int = Field(description="Index of the media file in the provided list (0-based)")
    start: float = Field(description="Start time of the segment in seconds")
    end: float = Field(description="End time of the segment in seconds")
    role: str = Field(description="Narrative role (e.g., Hook, Build-up, Climax, Resolution)", default="Content")
    content: str = Field(description="Brief description of what makes this segment interesting")


class CoherentMultiSegmentResponse(BaseModel):
    """
    Response containing multiple segments from different media files that together form a coherent short.
    """
    theme: str = Field(description="The identified common theme or story connecting the media files")
    story_arc_explanation: str = Field(description="Step-by-step reasoning of how these clips create a compelling narrative with a strong hook and definitive ending", default="")
    segments: list[CoherentSegmentResponse] = Field(description="List of segments from different media to stitch together")
    total_duration: float = Field(description="Total duration of all segments combined in seconds")


def _get_duration_tolerance(target_duration: int) -> int:
    # Keep short targets tight, then scale up gradually for longer videos.
    return max(
        MIN_DURATION_TOLERANCE_SECONDS,
        min(MAX_DURATION_TOLERANCE_SECONDS, round(target_duration * 0.10))
    )


def _get_duration_bounds(target_duration: int) -> tuple[float, float]:
    tolerance = _get_duration_tolerance(target_duration)
    min_total = max(1, target_duration - tolerance)
    max_total = target_duration + tolerance
    return float(min_total), float(max_total)


def _total_segment_duration(segments: list[dict]) -> float:
    return sum(max(0.0, float(segment['end']) - float(segment['start'])) for segment in segments)


def _trim_segments_to_max_total(
    segments: list[dict],
    max_total: float,
    min_segment_duration: float = 2.0
) -> list[dict]:
    trimmed_segments = []
    running_total = 0.0

    for segment in segments:
        start = float(segment['start'])
        end = float(segment['end'])
        duration = max(0.0, end - start)

        if duration <= 0:
            continue

        remaining = max_total - running_total
        if remaining <= 0:
            break

        if duration <= remaining:
            trimmed_segments.append(segment.copy())
            running_total += duration
            continue

        if remaining >= min_segment_duration:
            shortened_segment = segment.copy()
            shortened_segment['end'] = start + remaining
            trimmed_segments.append(shortened_segment)
            running_total += remaining
        break

    return trimmed_segments


def _pad_segments_to_min_total(
    segments: list[dict],
    min_total: float
) -> list[dict]:
    if not segments:
        return segments

    current_total = _total_segment_duration(segments)
    if current_total >= min_total:
        return segments

    shortfall = min_total - current_total
    padded_segments = [seg.copy() for seg in segments]
    
    padding_per_segment = shortfall / len(padded_segments)
    for i in range(len(padded_segments)):
        if shortfall <= 0:
            break
        current_seg = padded_segments[i]
        max_allowed_end = padded_segments[i+1]['start'] if i + 1 < len(padded_segments) else float('inf')
        
        available_room = max_allowed_end - current_seg['end']
        if available_room > 0:
            actual_pad = min(shortfall, min(padding_per_segment, available_room))
            current_seg['end'] += actual_pad
            shortfall -= actual_pad

    if shortfall > 0 and padded_segments:
        padded_segments[-1]['end'] += shortfall
        
    return padded_segments


def _is_within_target_window(total_duration: float, target_duration: int) -> bool:
    min_total, max_total = _get_duration_bounds(target_duration)
    return min_total <= total_duration <= max_total


def _format_user_prompt(user_prompt: Optional[str]) -> str:
    """Render an optional user-supplied editing prompt as an extra system block.

    Returns an empty string when no prompt is provided so callers can safely
    concatenate it onto an existing system message.
    """
    if not user_prompt or not str(user_prompt).strip():
        return ""
    cleaned = str(user_prompt).strip().replace("{", "{{").replace("}", "}}")
    return (
        "\n\nUSER EDITING INSTRUCTIONS (HIGH PRIORITY):\n"
        f"\"\"\"\n{cleaned}\n\"\"\"\n"
        "Treat the instructions above as the most important guidance for selection. "
        "Adjust which segments you pick (and their boundaries) so the resulting short clearly reflects this intent. "
        "Still respect the duration window and structural rules described earlier.\n"
    )


def _build_duration_retry_message(
    target_duration: int,
    actual_total: float,
    min_total: float,
    max_total: float,
    extra_rules: Optional[list[str]] = None
) -> str:
    direction = "longer" if actual_total < min_total else "shorter"
    rules = "\n".join(f"- {rule}" for rule in (extra_rules or []))
    if rules:
        rules = f"\nAdditional rules:\n{rules}"

    return (
        f"The previous plan totaled {actual_total:.2f}s. That is outside the required window of "
        f"{min_total:.0f}s to {max_total:.0f}s for a {target_duration}s target.\n"
        f"Regenerate the full plan so the combined duration lands inside that window.\n"
        f"Make it {direction} while keeping the pacing strong and the chosen moments complete."
        f"{rules}"
    )


def _parse_multi_segments(response_segments, item_label="Segment", max_segment_duration: Optional[float] = None):
    segments = []
    total_duration = 0.0

    for i, segment in enumerate(response_segments, 1):
        try:
            start = float(segment.start)
            end = float(segment.end)

            if start < 0 or end < 0:
                print(f"  Warning: {item_label} {i} has negative time - skipping")
                continue

            if end <= start:
                print(f"  Warning: {item_label} {i} has invalid time range (start >= end) - skipping")
                continue

            duration = end - start
            if max_segment_duration is not None and duration > max_segment_duration:
                print(
                    f"  Warning: {item_label} {i} is {duration:.1f}s "
                    f"(exceeds {max_segment_duration:.0f}s max) - truncating"
                )
                end = start + max_segment_duration
                duration = max_segment_duration

            segments.append({
                'start': start,
                'end': end,
                'role': getattr(segment, 'role', 'Segment'),
                'content': segment.content
            })
            total_duration += duration

        except (ValueError, TypeError) as e:
            print(f"  Warning: Could not parse {item_label.lower()} {i}: {e}")
            continue

    return segments, total_duration


system = """
The input contains a timestamped transcription of a video.
Select a highly engaging segment (around 1-2 minutes) from the transcription that contains something interesting, useful, surprising, controversial, or thought-provoking.

CRITICAL REQUIREMENTS:
1. STRONG HOOK: The segment MUST start at a moment that immediately grabs attention. Do not start with boring context.
2. NARRATIVE: The selected text should form a complete thought and tell a mini-story.
3. DEFINITIVE ENDING: The segment MUST end with a satisfying conclusion, punchline, or resolution. DO NOT cut off mid-sentence or mid-idea.
4. COMPLETE SENTENCES: Do not cut sentences in the middle.

Return a JSON object with the following structure:
## Output 
{{
    "reasoning": "Think step-by-step. Explain the hook, the main point, and why the ending feels complete.",
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




def GetHighlight(Transcription, user_prompt: Optional[str] = None):
    from langchain_openai import ChatOpenAI

    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",  # Much cheaper than gpt-4o
            temperature=1.0,
            api_key = api_key
        )

        from langchain.prompts import ChatPromptTemplate
        system_message = system + _format_user_prompt(user_prompt)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_message),
                ("user", Transcription)
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
        if hasattr(response, 'reasoning') and response.reasoning:
            print(f"Reasoning: {response.reasoning}")
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


def GetHighlightMultiSegment(Transcription, target_duration=120, user_prompt: Optional[str] = None):
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
    
    min_total, max_total = _get_duration_bounds(target_duration)

    multi_system = f"""
The input contains a timestamped transcription of a video.
Identify separate segments from throughout the transcription that together form an engaging and cohesive short video.
Select segments that contain interesting, useful, surprising, controversial, or thought-provoking content.
The segments should complement each other and tell a compelling story together.
The combined duration MUST land between {min_total:.0f} and {max_total:.0f} seconds.
Aim as close as possible to {target_duration} seconds across all segments combined.
Each segment should contain only complete sentences - do not cut sentences in the middle.
Return as many segments as needed to hit the duration window cleanly.
The FIRST segment should work as a strong hook.
The FINAL segment must feel like a real ending: a conclusion, payoff, reaction, punchline, summary line, or natural closing beat.
Do NOT end the final segment in the middle of a sentence, mid-thought, or right before the payoff lands.
If needed, sacrifice a little duration earlier so the ending feels complete and satisfying.

Return a JSON object with the following structure:
{{{{
    "story_arc_explanation": "Think step-by-step about the story arc. Explain the hook, the context, and the final payoff.",
    "segments": [
        {{{{
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "role": "Hook | Context | Climax | Resolution",
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
        multi_system_with_prompt = multi_system + _format_user_prompt(user_prompt)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", multi_system_with_prompt),
                ("user", Transcription)
            ]
        )
        chain = prompt | llm.with_structured_output(MultiSegmentResponse, method="function_calling")

        print(f"Calling LLM for multi-segment selection (target: {target_duration}s, window: {min_total:.0f}-{max_total:.0f}s)...")

        response = None
        segments = []
        total_duration = 0.0
        retry_message = None

        for attempt in range(1, MAX_DURATION_PLANNING_ATTEMPTS + 1):
            messages = {"Transcription": Transcription}
            if retry_message:
                print(f"Retrying duration planning ({attempt}/{MAX_DURATION_PLANNING_ATTEMPTS})...")
                response = chain.invoke({**messages, "Transcription": f"{Transcription}\n\nPLANNING FEEDBACK:\n{retry_message}"})
            else:
                response = chain.invoke(messages)

            if not response:
                print("ERROR: LLM returned empty response")
                return None

            if not hasattr(response, 'segments') or not response.segments:
                print("ERROR: Invalid response structure or no segments returned")
                return None

            segments, total_duration = _parse_multi_segments(response.segments, item_label="Segment")
            if segments and _is_within_target_window(total_duration, target_duration):
                break

            retry_message = _build_duration_retry_message(
                target_duration,
                total_duration,
                min_total,
                max_total,
                extra_rules=[
                    "Keep complete thoughts and avoid cutting sentences mid-idea.",
                    "Adjust the number of segments and their lengths so the total duration fits the required window.",
                    "Make sure the first segment hooks quickly and the final segment feels like a real ending, not an abrupt cutoff."
                ]
            )

        if total_duration > max_total:
            segments = _trim_segments_to_max_total(segments, max_total)
            total_duration = _total_segment_duration(segments)
        elif total_duration < min_total:
            segments = _pad_segments_to_min_total(segments, min_total)
            total_duration = _total_segment_duration(segments)

        print(f"\n{'='*60}")
        if hasattr(response, 'story_arc_explanation') and response.story_arc_explanation:
            print(f"STORY ARC: {response.story_arc_explanation}")
        print(f"SELECTED {len(segments)} SEGMENTS:")
        print(f"{'='*60}")
        for i, segment in enumerate(segments, 1):
            duration = segment['end'] - segment['start']
            role = segment.get('role', 'Segment')
            print(f"  Segment {i} [{role}]: {segment['start']:.2f}s - {segment['end']:.2f}s ({duration:.2f}s)")
            print(f"    Content: {segment['content']}")
        
        print(f"\nTotal duration: {total_duration:.2f}s (target: {target_duration}s, allowed: {min_total:.0f}-{max_total:.0f}s)")
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
    
    min_total, max_total = _get_duration_bounds(target_duration)

    scene_system = f"""
You are analyzing a video that has been split into detected scenes with associated transcripts.
Your task is to select important scenes that together form an engaging and cohesive short video.
Choose scenes that contain interesting, useful, surprising, controversial, or thought-provoking content.
The selected scenes should complement each other and tell a compelling story.
The combined duration MUST land between {min_total:.0f} and {max_total:.0f} seconds.
Aim as close as possible to {target_duration} seconds.
The FIRST scene should act as a hook.
The FINAL scene must feel like a natural ending with a sense of resolution, payoff, reaction, or conclusion.
Do NOT end on a scene that feels like it obviously continues.

Analyze the scene boundaries and transcripts, then select whole scenes (don't split them).
Return a JSON object with the following structure:
{{{{
    "story_arc_explanation": "Think step-by-step about the story arc. Explain the hook, the context, and the final payoff.",
    "segments": [
        {{{{
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "role": "Hook | Context | Climax | Resolution",
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
                ("user", "{planning_request}")
            ]
        )
        chain = prompt | llm.with_structured_output(MultiSegmentResponse, method="function_calling")
        
        print(f"Calling LLM for scene-based selection (target: {target_duration}s, window: {min_total:.0f}-{max_total:.0f}s)...")

        response = None
        segments = []
        total_duration = 0.0
        user_message = "Please select the most important scenes for the short video."

        for attempt in range(1, MAX_DURATION_PLANNING_ATTEMPTS + 1):
            if attempt > 1:
                print(f"Retrying scene duration planning ({attempt}/{MAX_DURATION_PLANNING_ATTEMPTS})...")
            response = chain.invoke({"planning_request": user_message})

            if not response:
                print("ERROR: LLM returned empty response")
                return None

            if not hasattr(response, 'segments') or not response.segments:
                print("ERROR: Invalid response structure or no segments returned")
                return None

            segments, total_duration = _parse_multi_segments(response.segments, item_label="Scene")
            if segments and _is_within_target_window(total_duration, target_duration):
                break

            user_message = _build_duration_retry_message(
                target_duration,
                total_duration,
                min_total,
                max_total,
                extra_rules=[
                    "Select whole scenes only.",
                    "Change the scene count if needed so the total duration fits the required window.",
                    "Make the last selected scene feel like a proper ending instead of an abrupt stop."
                ]
            )

        if total_duration > max_total:
            segments = _trim_segments_to_max_total(segments, max_total)
            total_duration = _total_segment_duration(segments)
        elif total_duration < min_total:
            segments = _pad_segments_to_min_total(segments, min_total)
            total_duration = _total_segment_duration(segments)

        print(f"\n{'='*60}")
        if hasattr(response, 'story_arc_explanation') and response.story_arc_explanation:
            print(f"STORY ARC: {response.story_arc_explanation}")
        print(f"SELECTED {len(segments)} SCENES:")
        print(f"{'='*60}")
        for i, segment in enumerate(segments, 1):
            duration = segment['end'] - segment['start']
            role = segment.get('role', 'Segment')
            print(f"  Scene {i} [{role}]: {segment['start']:.2f}s - {segment['end']:.2f}s ({duration:.2f}s)")
            print(f"    Reason: {segment['content']}")
        
        print(f"\nTotal duration: {total_duration:.2f}s (target: {target_duration}s, allowed: {min_total:.0f}-{max_total:.0f}s)")
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


def GetHighlightMultiSegmentFromFrames(scene_segments, target_duration=120, user_prompt: Optional[str] = None):
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
    
    min_total, max_total = _get_duration_bounds(target_duration)
    
    scene_system = f"""
You are analyzing a video and selecting the most important and memorable scenes based on their visual content.
Each scene has been analyzed to describe what's happening visually (people, activities, emotions, settings).

Your task is to select scenes that together create a compelling short video.

DURATION REQUIREMENTS:
- MAXIMUM 10 seconds per segment (strict limit)
- Exception: Only use up to 20s if the moment is EXTREMELY important (e.g., main subject/couple interaction)
- REQUIRED total duration window: {min_total:.0f} to {max_total:.0f} seconds
- TARGET total duration: {target_duration} seconds
- You MUST keep the final total inside that window
- The FIRST segment should hook the viewer quickly
- The FINAL segment must feel like a closing beat, payoff, reaction, or visual resolution
- Do NOT end mid-action or on a moment that clearly feels unfinished

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
    "story_arc_explanation": "Think step-by-step about the story arc. Explain the hook, the context, and the final payoff.",
    "segments": [
        {{{{
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "role": "Hook | Context | Climax | Resolution",
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
        scene_system_with_prompt = scene_system + _format_user_prompt(user_prompt)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", scene_system_with_prompt),
                ("user", "{planning_request}")
            ]
        )
        chain = prompt | llm.with_structured_output(MultiSegmentResponse, method="function_calling")

        print(f"Calling LLM for scene selection based on visual content...")
        print(f"Target: {target_duration}s, Allowed window: {min_total:.0f}-{max_total:.0f}s")
        print(f"Max per segment: 10s (20s only for critical moments)")

        response = None
        segments = []
        total_duration = 0.0
        user_message = (
            f"Create a {target_duration}s video. Keep the total between {min_total:.0f}s and {max_total:.0f}s. "
            "Use 10s max per clip normally. Only go to 20s if absolutely critical. "
            "Select or split scenes as needed to hit the duration window while keeping clips punchy."
        )

        for attempt in range(1, MAX_DURATION_PLANNING_ATTEMPTS + 1):
            if attempt > 1:
                print(f"Retrying visual scene duration planning ({attempt}/{MAX_DURATION_PLANNING_ATTEMPTS})...")
            response = chain.invoke({"planning_request": user_message})

            if not response:
                print("ERROR: LLM returned empty response")
                return None

            if not hasattr(response, 'segments') or not response.segments:
                print("ERROR: Invalid response structure or no segments returned")
                return None

            segments, total_duration = _parse_multi_segments(
                response.segments,
                item_label="Segment",
                max_segment_duration=20.0
            )
            if segments and _is_within_target_window(total_duration, target_duration):
                break

            user_message = _build_duration_retry_message(
                target_duration,
                total_duration,
                min_total,
                max_total,
                extra_rules=[
                    "Keep clips short and punchy.",
                    "Use 10s max per clip normally and only exceed that when absolutely necessary.",
                    "Add, remove, split, or shorten scenes so the combined duration fits the required window.",
                    "Make the last selected segment feel like a deliberate ending instead of an abrupt cutoff."
                ]
            )

        if total_duration > max_total:
            segments = _trim_segments_to_max_total(segments, max_total)
            total_duration = _total_segment_duration(segments)
        elif total_duration < min_total:
            segments = _pad_segments_to_min_total(segments, min_total)
            total_duration = _total_segment_duration(segments)

        print(f"\n{'='*60}")
        if hasattr(response, 'story_arc_explanation') and response.story_arc_explanation:
            print(f"STORY ARC: {response.story_arc_explanation}")
        print(f"SELECTED {len(segments)} SEGMENTS:")
        print(f"{'='*60}")
        for i, segment in enumerate(segments, 1):
            duration = segment['end'] - segment['start']
            role = segment.get('role', 'Segment')
            if duration > 10:
                print(f"  Note: Segment {i} is {duration:.1f}s (above 10s standard, but acceptable)")
            print(f"  Segment {i} [{role}]: {segment['start']:.2f}s - {segment['end']:.2f}s ({duration:.2f}s)")
            print(f"    Reason: {segment['content']}")

        print(f"\nTotal duration: {total_duration:.2f}s (target: {target_duration}s, allowed: {min_total:.0f}-{max_total:.0f}s)")
        
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


def GetCoherentHighlights(media_metadata_list, target_duration=120, user_prompt: Optional[str] = None):
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
6. For images, you can assume they will be shown for 1-2 seconds max.
7. For videos, select highly engaging, fast-paced segments (2-6s typically) to retain low-attention-span viewers.
8. The final result should feel like a single, well-paced story featuring ALL provided media files.

DURATION REQUIREMENTS:
 TARGET total duration: {target_duration} seconds. You must be strictly close to this duration.
- Each segment should be meaningful and follow the identified theme.

Return a JSON object with the following structure:
{{{{
    "theme": "Description of the identified theme",
    "story_arc_explanation": "Think step-by-step about how these selected media files form a compelling narrative arc.",
    "segments": [
        {{{{
            "media_index": <index of the media file (number)>,
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "role": "Hook | Context | Climax | Resolution",
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
        coherent_system_with_prompt = coherent_system + _format_user_prompt(user_prompt)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", coherent_system_with_prompt),
                ("user", "{planning_request}")
            ]
        )
        chain = prompt | llm.with_structured_output(CoherentMultiSegmentResponse, method="function_calling")
        
        min_total, max_total = _get_duration_bounds(target_duration)
        print(f"Calling LLM for coherent multi-media selection (target: {target_duration}s, window: {min_total:.0f}-{max_total:.0f}s)...")
        
        response = None
        segments = []
        total_duration = 0.0
        user_message = f"Find the best connection between these {len(media_metadata_list)} files and create a {target_duration}s coherent short."
        
        for attempt in range(1, MAX_DURATION_PLANNING_ATTEMPTS + 1):
            if attempt > 1:
                print(f"Retrying coherent duration planning ({attempt}/{MAX_DURATION_PLANNING_ATTEMPTS})...")
                
            response = chain.invoke({"planning_request": user_message})
            
            if not response:
                print("ERROR: LLM returned empty response")
                return None
            
            if not hasattr(response, 'segments') or not response.segments:
                print("ERROR: No segments returned")
                return None
            
            segments = []
            for i, segment in enumerate(response.segments, 1):
                try:
                    media_idx = int(segment.media_index)
                    media_type = media_metadata_list[media_idx]['type'] if media_idx < len(media_metadata_list) else 'video'
                    
                    start = float(segment.start)
                    end = float(segment.end)
                    
                    if media_type == 'image':
                        # Strictly cap image durations so LLM calculations match actual processor output
                        duration = min(max(end - start, 0.5), 2.0)
                        end = start + duration

                    segments.append({
                        'media_index': media_idx,
                        'start': start,
                        'end': end,
                        'role': getattr(segment, 'role', 'Segment'),
                        'content': segment.content
                    })
                except Exception as e:
                    print(f"  Warning: Skipping invalid segment {i}: {e}")
            
            total_duration = _total_segment_duration(segments)
            if segments and _is_within_target_window(total_duration, target_duration):
                break
                
            user_message = _build_duration_retry_message(
                target_duration,
                total_duration,
                min_total,
                max_total,
                extra_rules=[
                    "Make sure to include at least one segment from EVERY SINGLE original file index.",
                    "For images, keep them strictly between 1 and 2 seconds long.",
                    "If the video is too short, select longer segments from the video files.",
                    "Ensure the total combined duration meets the target."
                ]
            )
            
        print(f"\n{'='*60}")
        print(f"IDENTIFIED THEME: {response.theme}")
        if hasattr(response, 'story_arc_explanation') and response.story_arc_explanation:
            print(f"STORY ARC: {response.story_arc_explanation}")
        print(f"SELECTED {len(segments)} SEGMENTS:")
        print(f"{'='*60}")
        for i, segment in enumerate(segments, 1):
            role = segment.get('role', 'Segment')
            print(f"  Segment {i} [{role}]: Media {segment['media_index']} | {segment['start']:.2f}s - {segment['end']:.2f}s")
            print(f"    Reason: {segment['content']}")
        
        # Strictly enforce target duration bounds
        if total_duration > max_total:
            segments = _trim_segments_to_max_total(segments, max_total)
        elif total_duration < min_total:
            # Custom padding for coherent highlights (only pad video segments)
            shortfall = min_total - total_duration
            video_segments = [s for s in segments if media_metadata_list[s['media_index']]['type'] == 'video']
            
            if video_segments and shortfall > 0:
                pad_per_seg = shortfall / len(video_segments)
                for s in video_segments:
                    media_dur = media_metadata_list[s['media_index']]['duration']
                    available = media_dur - s['end']
                    pad = min(pad_per_seg, available)
                    if pad > 0:
                        s['end'] += pad
                        shortfall -= pad
                
                # If still shortfall, pad the last video segment as much as possible
                if shortfall > 0 and video_segments:
                    last_vid_seg = video_segments[-1]
                    media_dur = media_metadata_list[last_vid_seg['media_index']]['duration']
                    available = media_dur - last_vid_seg['end']
                    pad = min(shortfall, available)
                    if pad > 0:
                        last_vid_seg['end'] += pad
        
        total_dur = _total_segment_duration(segments)
        print(f"Trimmed/Padded Total duration: {total_dur:.2f}s")
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
