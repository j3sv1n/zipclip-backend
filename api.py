"""
ZipClip Backend API Server
FastAPI server for video processing with frontend integration support.
"""

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks, Header, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import json
import os
import uuid
import threading
import time
from datetime import datetime
from processor import process_video, process_multi_media
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="ZipClip Backend API",
    description="AI-powered video processing API for creating YouTube Shorts",
    version="1.0.0"
)

# Configure CORS
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
if cors_origins_env == "*":
    cors_origins = ["*"]
else:
    cors_origins = cors_origins_env.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job storage (in-memory, consider Redis for production)
jobs: Dict[str, Dict] = {}
jobs_lock = threading.Lock()

# Configuration
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "3"))
UPLOAD_MAX_SIZE = int(os.getenv("UPLOAD_MAX_SIZE", "500000000"))  # 500MB default
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Pydantic Models
class SubtitleConfig(BaseModel):
    """Subtitle styling options (matching Subtitles.py defaults)"""
    font: str = Field("Montserrat-ExtraBold", description="Font name")
    fontsize: int = Field(80, description="Font size in pixels", ge=20, le=200)
    color: str = Field("#2699ff", description="Text color (hex code)")
    stroke_color: str = Field("black", description="Outline color (hex code)")
    stroke_width: int = Field(2, description="Outline width in pixels", ge=0, le=10)


class LLMConfig(BaseModel):
    """LLM configuration options for highlight selection"""
    model: str = Field("gpt-4o-mini", description="OpenAI model to use")
    temperature: float = Field(1.0, description="Sampling temperature", ge=0.0, le=2.0)


class ProcessRequest(BaseModel):
    # Input
    video_url: Optional[str] = Field(None, description="YouTube URL or video URL")
    
    # Processing options
    mode: str = Field("continuous", description="Processing mode: continuous, multi_segment, scene_based")
    add_subtitles: bool = Field(True, description="Whether to add subtitles to the video")
    target_duration: int = Field(120, description="Target duration in seconds for multi-segment modes", ge=30, le=300)
    
    # Batch processing
    auto_approve: bool = Field(True, description="Automatically approve segments without review (batch mode)")
    
    # Advanced configuration
    subtitle_config: Optional[SubtitleConfig] = Field(None, description="Custom subtitle styling")
    llm_config: Optional[LLMConfig] = Field(None, description="LLM model and parameters for highlight selection")
    
    # Optional natural-language editing prompt
    user_prompt: Optional[str] = Field(None, description="Optional natural-language instructions to steer how the AI edits the video")

    # Return options for frontend review
    return_transcript: bool = Field(False, description="Return transcription with results")
    return_segments_preview: bool = Field(False, description="Return segment preview before final processing (experimental)")


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    created_at: str
    completed_at: Optional[str] = None
    output_file: Optional[str] = None
    error: Optional[str] = None
    video_title: Optional[str] = None
    segments: Optional[List[Dict]] = None
    transcript: Optional[List[Dict]] = None  # Full transcript with timestamps
    processing_mode: Optional[str] = None  # The mode used for processing
    target_duration_used: Optional[int] = None  # Target duration that was used
    user_prompt: Optional[str] = None  # The editing prompt that produced this job
    parent_job_id: Optional[str] = None  # If this job is a refinement, the job it derives from


class RefineRequest(BaseModel):
    refinement_prompt: str = Field(..., description="Natural-language description of changes to apply", min_length=1)


class JobListItem(BaseModel):
    job_id: str
    status: str
    progress: int
    created_at: str
    video_title: Optional[str] = None


# Background job processor
def process_job(job_id: str, input_source: any, mode: str, add_subtitles: bool, target_duration: int, user_prompt: Optional[str] = None):
    """Background task to process video."""

    def update_progress(message: str, percent: int):
        """Update job progress."""
        with jobs_lock:
            if job_id in jobs:
                jobs[job_id]["progress"] = percent
                jobs[job_id]["message"] = message
                jobs[job_id]["status"] = "processing"

    try:
        with jobs_lock:
            jobs[job_id]["status"] = "processing"
            jobs[job_id]["message"] = "Starting processing..."

        # Process the video
        if isinstance(input_source, list):
            # Multiple local files
            result = process_multi_media(
                file_paths=input_source,
                add_subtitles=add_subtitles,
                target_duration=target_duration,
                progress_callback=update_progress,
                session_id=job_id,
                mode=mode,
                user_prompt=user_prompt
            )
        else:
            # Single URL or local file
            result = process_video(
                video_url_or_path=input_source,
                mode=mode,
                add_subtitles=add_subtitles,
                target_duration=target_duration,
                progress_callback=update_progress,
                session_id=job_id,
                user_prompt=user_prompt
            )
        
        with jobs_lock:
            if result["success"]:
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["progress"] = 100
                jobs[job_id]["message"] = "Processing complete"
                jobs[job_id]["output_file"] = result["output_file"]
                jobs[job_id]["video_title"] = result.get("video_title")
                jobs[job_id]["segments"] = result.get("segments")
            else:
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["message"] = "Processing failed"
                jobs[job_id]["error"] = result.get("error", "Unknown error")
            
            jobs[job_id]["completed_at"] = datetime.now().isoformat()
    
    except Exception as e:
        with jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["message"] = "Processing failed"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["completed_at"] = datetime.now().isoformat()


# API Endpoints

@app.get("/api/info")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ZipClip Backend API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "process": "/api/process",
            "status": "/api/status/{job_id}",
            "download": "/api/download/{job_id}",
            "jobs": "/api/jobs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": len([j for j in jobs.values() if j["status"] in ["pending", "processing"]])
    }


@app.post("/api/process", response_model=JobStatus)
async def create_processing_job(
    background_tasks: BackgroundTasks,
    request: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    mode: str = "continuous",
    add_subtitles: bool = True,
    target_duration: int = 120,
    auto_approve: bool = True,
    x_client_id: str = Header("anonymous")
):
    # Parse the JSON string form field into a ProcessRequest model.
    # If the value is not valid JSON (e.g. Swagger's "string" placeholder),
    # silently ignore it and fall back to query parameters.
    parsed_request: Optional[ProcessRequest] = None
    if request:
        try:
            data = json.loads(request)
            if isinstance(data, dict):
                parsed_request = ProcessRequest(**data)
        except (json.JSONDecodeError, ValueError):
            pass  # Not valid JSON — fall back to query params
    """
    Submit a video processing job.
    
    Accepts either a JSON body with video_url or a file upload.
    
    **Request Body (JSON):**
    - video_url: YouTube URL or video URL
    - mode: 'continuous', 'multi_segment', or 'scene_based'
    - add_subtitles: Whether to add subtitles (default: true)
    - target_duration: Target duration in seconds (30-300, default: 120)
    - auto_approve: Auto-approve segments for batch processing (default: true)
    - subtitle_config: Custom subtitle styling options
    - llm_config: Custom LLM model and parameters
    - return_transcript: Return full transcript in response (default: false)
    - return_segments_preview: Return segment preview (default: false)
    
    **Query Parameters (for file upload):**
    - mode, add_subtitles, target_duration, auto_approve
    """
    
    # Check concurrent job limit
    active_jobs = len([j for j in jobs.values() if j["status"] in ["pending", "processing"]])
    if active_jobs >= MAX_CONCURRENT_JOBS:
        raise HTTPException(status_code=429, detail="Maximum concurrent jobs reached. Please try again later.")
    
    # Determine input source and extract options
    input_source = None
    processing_mode = mode
    process_subtitles = add_subtitles
    process_duration = target_duration
    process_user_prompt: Optional[str] = None
    job_id = str(uuid.uuid4())[:8]

    if files:
        # Handle file upload (one or many)
        input_source = []
        for i, file in enumerate(files):
            if file.size and file.size > UPLOAD_MAX_SIZE:
                raise HTTPException(status_code=413, detail=f"File {file.filename} too large.")

            file_extension = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
            video_path = os.path.join(UPLOAD_DIR, f"{job_id}_{i}{file_extension}")

            with open(video_path, "wb") as f:
                content = await file.read()
                f.write(content)
            input_source.append(video_path)

        # If only one file, we might still treat it as single-video if user wants,
        # but the request structure now supports list.
        # If multiple files, we force 'coherent' processing if needed, but processor handles it.
        if len(input_source) == 1:
            input_source = input_source[0]

        # When uploading files, mode/subtitles/duration come from query params (preserves prior behaviour).
        # user_prompt is a new field with no query-param equivalent, so it's only carried via the JSON body.
        if parsed_request:
            process_user_prompt = parsed_request.user_prompt

    elif parsed_request and parsed_request.video_url:
        # Handle URL
        input_source = parsed_request.video_url
        processing_mode = parsed_request.mode
        process_subtitles = parsed_request.add_subtitles
        process_duration = parsed_request.target_duration
        process_user_prompt = parsed_request.user_prompt

    else:
        raise HTTPException(status_code=400, detail="Either video_url or files must be provided")

    # Normalise empty/whitespace-only prompts to None
    if process_user_prompt is not None and not str(process_user_prompt).strip():
        process_user_prompt = None

    # Create job entry with additional info
    with jobs_lock:
        jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": 0,
            "message": "Job queued",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "output_file": None,
            "error": None,
            "video_title": None,
            "segments": None,
            "transcript": None,
            "processing_mode": processing_mode,
            "target_duration_used": process_duration,
            "user_prompt": process_user_prompt,
            "parent_job_id": None,
            # Internal-only fields for refinement support (excluded from JobStatus model)
            "_input_source": input_source,
            "_add_subtitles": process_subtitles,
            "_client_id": x_client_id,
        }

    # Start background processing
    background_tasks.add_task(
        process_job,
        job_id=job_id,
        input_source=input_source,
        mode=processing_mode,
        add_subtitles=process_subtitles,
        target_duration=process_duration,
        user_prompt=process_user_prompt
    )

    return JobStatus(**{k: v for k, v in jobs[job_id].items() if not k.startswith("_")})


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str, x_client_id: str = Header("anonymous")):
    """Get status of a processing job."""
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = jobs[job_id]
        if job.get("_client_id") != x_client_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this job")

        return JobStatus(**{k: v for k, v in job.items() if not k.startswith("_")})


@app.post("/api/refine/{job_id}", response_model=JobStatus)
async def refine_job(job_id: str, refine_request: RefineRequest, background_tasks: BackgroundTasks, x_client_id: str = Header("anonymous")):
    """
    Create a refinement job that re-processes the same input as `job_id`
    with an additional natural-language change request.
    """
    refinement_text = refine_request.refinement_prompt.strip()
    if not refinement_text:
        raise HTTPException(status_code=400, detail="Refinement prompt cannot be empty")

    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        parent = jobs[job_id]
        if parent.get("_client_id") != x_client_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this job")

        if parent["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Parent job not completed. Current status: {parent['status']}"
            )

        parent_input = parent.get("_input_source")
        if parent_input is None:
            raise HTTPException(
                status_code=400,
                detail="Parent job did not preserve its input source and cannot be refined."
            )

        # Validate that uploaded files still exist on disk
        if isinstance(parent_input, list):
            missing = [p for p in parent_input if not os.path.exists(p)]
            if missing:
                raise HTTPException(
                    status_code=410,
                    detail=f"Original uploaded files no longer exist: {', '.join(os.path.basename(m) for m in missing)}"
                )
        elif isinstance(parent_input, str) and not (
            parent_input.startswith("http://") or parent_input.startswith("https://")
        ):
            if not os.path.exists(parent_input):
                raise HTTPException(
                    status_code=410,
                    detail="Original uploaded file no longer exists."
                )

        # Combine prior prompt (if any) with the new refinement so the LLM sees full intent
        prior_prompt = parent.get("user_prompt")
        if prior_prompt:
            combined_prompt = (
                f"Previous editing instructions: {prior_prompt}\n\n"
                f"Requested changes after reviewing the previous result: {refinement_text}\n\n"
                "Apply the requested changes while keeping anything from the previous instructions that the user did not contradict."
            )
        else:
            combined_prompt = (
                f"Requested changes after reviewing a previous version of this short: {refinement_text}\n\n"
                "Adjust the segment selection so the new result reflects this feedback."
            )

        # Concurrent-job ceiling
        active_jobs = len([j for j in jobs.values() if j["status"] in ["pending", "processing"]])
        if active_jobs >= MAX_CONCURRENT_JOBS:
            raise HTTPException(status_code=429, detail="Maximum concurrent jobs reached. Please try again later.")

        new_job_id = str(uuid.uuid4())[:8]
        jobs[new_job_id] = {
            "job_id": new_job_id,
            "status": "pending",
            "progress": 0,
            "message": "Refinement queued",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "output_file": None,
            "error": None,
            "video_title": parent.get("video_title"),
            "segments": None,
            "transcript": None,
            "processing_mode": parent.get("processing_mode"),
            "target_duration_used": parent.get("target_duration_used"),
            "user_prompt": combined_prompt,
            "parent_job_id": job_id,
            "_input_source": parent_input,
            "_add_subtitles": parent.get("_add_subtitles", True),
            "_client_id": x_client_id,
        }

        new_job_snapshot = {k: v for k, v in jobs[new_job_id].items() if not k.startswith("_")}

    background_tasks.add_task(
        process_job,
        job_id=new_job_id,
        input_source=parent_input,
        mode=parent.get("processing_mode") or "continuous",
        add_subtitles=parent.get("_add_subtitles", True),
        target_duration=parent.get("target_duration_used") or 120,
        user_prompt=combined_prompt
    )

    return JobStatus(**new_job_snapshot)


@app.get("/api/preview/{job_id}")
async def preview_result(job_id: str, client_id: str = Query("anonymous")):
    """Stream the processed video inline for in-browser preview."""
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = jobs[job_id]
        if job.get("_client_id") != client_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this job")

        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail=f"Job not completed. Current status: {job['status']}")

        output_file = job.get("output_file")

    if not output_file or not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="Output file not found")

    filename = os.path.basename(output_file)

    return FileResponse(
        path=output_file,
        media_type="video/mp4",
        filename=filename,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "bytes",
        }
    )


@app.get("/api/download/{job_id}")
async def download_result(job_id: str, client_id: str = Query("anonymous")):
    """Download the processed video."""
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = jobs[job_id]
        if job.get("_client_id") != client_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this job")
        
        if job["status"] != "completed":
            raise HTTPException(status_code=400, detail=f"Job not completed. Current status: {job['status']}")
        
        output_file = job.get("output_file")
        
        if not output_file or not os.path.exists(output_file):
            raise HTTPException(status_code=404, detail="Output file not found")
        
        filename = os.path.basename(output_file)
        
        return FileResponse(
            path=output_file,
            media_type="video/mp4",
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )


@app.get("/api/jobs", response_model=List[JobListItem])
async def list_jobs(status: Optional[str] = None, limit: int = 50, x_client_id: str = Header("anonymous")):
    """List all jobs, optionally filtered by status."""
    with jobs_lock:
        # Filter jobs by client_id first
        job_list = [j for j in jobs.values() if j.get("_client_id") == x_client_id]
        
        # Filter by status if provided
        if status:
            job_list = [j for j in job_list if j["status"] == status]
        
        # Sort by created_at descending
        job_list.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Limit results
        job_list = job_list[:limit]
        
        # Return simplified job items
        return [
            JobListItem(
                job_id=j["job_id"],
                status=j["status"],
                progress=j["progress"],
                created_at=j["created_at"],
                video_title=j.get("video_title")
            )
            for j in job_list
        ]


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str, x_client_id: str = Header("anonymous")):
    """Delete a job and its associated files."""
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = jobs[job_id]
        if job.get("_client_id") != x_client_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this job")
        
        # Don't delete if still processing
        if job["status"] == "processing":
            raise HTTPException(status_code=400, detail="Cannot delete job while processing")
        
        # Delete output file if exists
        output_file = job.get("output_file")
        if output_file and os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception as e:
                print(f"Warning: Could not delete output file: {e}")
        
        # Delete uploaded file if exists
        upload_path = os.path.join(UPLOAD_DIR, f"{job_id}*")
        import glob
        for f in glob.glob(upload_path):
            try:
                os.remove(f)
            except Exception as e:
                print(f"Warning: Could not delete upload file: {e}")
        
        # Remove from jobs dict
        del jobs[job_id]
        
        return {"message": "Job deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    # Hugging Face Spaces uses the PORT environment variable
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    
    print(f"Starting ZipClip API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
