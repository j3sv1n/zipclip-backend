"""
ZipClip Backend API Server
FastAPI server for video processing with frontend integration support.
"""

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import json
import os
import uuid
import threading
import time
from datetime import datetime
from processor import process_video
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
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
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
    font: str = Field("Franklin-Gothic", description="Font name")
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


class JobListItem(BaseModel):
    job_id: str
    status: str
    progress: int
    created_at: str
    video_title: Optional[str] = None


# Background job processor
def process_job(job_id: str, video_path: str, mode: str, add_subtitles: bool, target_duration: int):
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
        result = process_video(
            video_url_or_path=video_path,
            mode=mode,
            add_subtitles=add_subtitles,
            target_duration=target_duration,
            progress_callback=update_progress,
            session_id=job_id
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

@app.get("/")
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
    file: Optional[UploadFile] = File(None),
    mode: str = "continuous",
    add_subtitles: bool = True,
    target_duration: int = 120,
    auto_approve: bool = True
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
    video_path = None
    processing_mode = mode
    process_subtitles = add_subtitles
    process_duration = target_duration
    
    if file:
        # Handle file upload
        if file.size and file.size > UPLOAD_MAX_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large. Maximum size: {UPLOAD_MAX_SIZE} bytes")
        
        # Save uploaded file
        job_id = str(uuid.uuid4())[:8]
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
        video_path = os.path.join(UPLOAD_DIR, f"{job_id}{file_extension}")
        
        with open(video_path, "wb") as f:
            content = await file.read()
            f.write(content)
    
    elif parsed_request and parsed_request.video_url:
        # Handle URL
        job_id = str(uuid.uuid4())[:8]
        video_path = parsed_request.video_url
        processing_mode = parsed_request.mode
        process_subtitles = parsed_request.add_subtitles
        process_duration = parsed_request.target_duration
    
    else:
        raise HTTPException(status_code=400, detail="Either video_url or file must be provided")
    
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
            "target_duration_used": process_duration
        }
    
    # Start background processing
    background_tasks.add_task(
        process_job,
        job_id=job_id,
        video_path=video_path,
        mode=processing_mode,
        add_subtitles=process_subtitles,
        target_duration=process_duration
    )
    
    return JobStatus(**jobs[job_id])


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a processing job."""
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return JobStatus(**jobs[job_id])


@app.get("/api/download/{job_id}")
async def download_result(job_id: str):
    """Download the processed video."""
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = jobs[job_id]
        
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
async def list_jobs(status: Optional[str] = None, limit: int = 50):
    """List all jobs, optionally filtered by status."""
    with jobs_lock:
        job_list = list(jobs.values())
        
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
async def delete_job(job_id: str):
    """Delete a job and its associated files."""
    with jobs_lock:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = jobs[job_id]
        
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
    port = int(os.getenv("API_PORT", "8000"))
    
    print(f"Starting ZipClip API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
