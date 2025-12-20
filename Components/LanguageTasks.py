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
{{
    "segments": [
        {{
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "content": "Brief description of what makes this segment interesting"
        }},
        ...
    ],
    "total_duration": <sum of all segment durations in seconds (number)>
}}

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
{{
    "segments": [
        {{
            "start": <start time in seconds (number)>,
            "end": <end time in seconds (number)>,
            "content": "Why this scene is important"
        }},
        ...
    ],
    "total_duration": <sum of all scene durations in seconds (number)>
}}

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


if __name__ == "__main__":
    print(GetHighlight(User))
