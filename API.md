# ZipClip Backend API Documentation

## Overview

The ZipClip Backend API provides RESTful endpoints for AI-powered video processing. It converts long-form videos into engaging short-form content optimized for social media platforms like YouTube Shorts, TikTok, and Instagram Reels.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, no authentication is required. The API uses the OpenAI API key configured in the `.env` file.

## Endpoints

### Health Check

**GET** `/health`

Check the API server status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-11T21:30:00",
  "active_jobs": 2
}
```

---

### Submit Processing Job

**POST** `/api/process`

Submit a video for processing. Accepts either a YouTube URL or a file upload.

#### Option 1: Process from URL

**Request Body:**
```json
{
  "video_url": "https://youtu.be/dKMueTMW1Nw",
  "mode": "continuous",
  "add_subtitles": true,
  "target_duration": 120
}
```

**Parameters:**
- `video_url` (string, required): YouTube URL or video URL
- `mode` (string, optional): Processing mode - `continuous`, `multi_segment`, or `scene_based`. Default: `continuous`
- `add_subtitles` (boolean, optional): Whether to add subtitles. Default: `true`
- `target_duration` (integer, optional): Target duration in seconds (30-300). Default: `120`

**Example with curl:**
```bash
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtu.be/dKMueTMW1Nw",
    "mode": "multi_segment",
    "add_subtitles": true,
    "target_duration": 120
  }'
```

**Example with JavaScript fetch:**
```javascript
const response = await fetch('http://localhost:8000/api/process', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    video_url: 'https://youtu.be/dKMueTMW1Nw',
    mode: 'multi_segment',
    add_subtitles: true,
    target_duration: 120
  })
});

const data = await response.json();
console.log('Job ID:', data.job_id);
```

#### Option 2: Upload Video File

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: File with key `file`

**Example with curl:**
```bash
curl -X POST http://localhost:8000/api/process \
  -F "file=@/path/to/video.mp4"
```

**Example with JavaScript FormData:**
```javascript
const formData = new FormData();
formData.append('file', videoFile); // videoFile is a File object

const response = await fetch('http://localhost:8000/api/process', {
  method: 'POST',
  body: formData
});

const data = await response.json();
console.log('Job ID:', data.job_id);
```

**Response:**
```json
{
  "job_id": "a1b2c3d4",
  "status": "pending",
  "progress": 0,
  "message": "Job queued",
  "created_at": "2026-02-11T21:30:00",
  "completed_at": null,
  "output_file": null,
  "error": null,
  "video_title": null,
  "segments": null
}
```

---

### Get Job Status

**GET** `/api/status/{job_id}`

Get the current status of a processing job.

**Parameters:**
- `job_id` (path parameter): The job ID returned from the process endpoint

**Example:**
```bash
curl http://localhost:8000/api/status/a1b2c3d4
```

**Response (Processing):**
```json
{
  "job_id": "a1b2c3d4",
  "status": "processing",
  "progress": 65,
  "message": "Selecting important scenes...",
  "created_at": "2026-02-11T21:30:00",
  "completed_at": null,
  "output_file": null,
  "error": null,
  "video_title": "my-awesome-video",
  "segments": null
}
```

**Response (Completed):**
```json
{
  "job_id": "a1b2c3d4",
  "status": "completed",
  "progress": 100,
  "message": "Processing complete",
  "created_at": "2026-02-11T21:30:00",
  "completed_at": "2026-02-11T21:35:00",
  "output_file": "output_videos/my-awesome-video_a1b2c3d4_short.mp4",
  "error": null,
  "video_title": "my-awesome-video",
  "segments": [
    {"start": 10.5, "end": 50.2},
    {"start": 75.8, "end": 120.5}
  ]
}
```

**Response (Failed):**
```json
{
  "job_id": "a1b2c3d4",
  "status": "failed",
  "progress": 30,
  "message": "Processing failed",
  "created_at": "2026-02-11T21:30:00",
  "completed_at": "2026-02-11T21:32:00",
  "output_file": null,
  "error": "Failed to download video",
  "video_title": null,
  "segments": null
}
```

**Status Values:**
- `pending`: Job is queued
- `processing`: Job is being processed
- `completed`: Job finished successfully
- `failed`: Job failed with error

---

### Download Processed Video

**GET** `/api/download/{job_id}`

Download the processed video file.

**Parameters:**
- `job_id` (path parameter): The job ID

**Example:**
```bash
curl http://localhost:8000/api/download/a1b2c3d4 -o output.mp4
```

**JavaScript Example:**
```javascript
// Download and create a blob URL
const response = await fetch(`http://localhost:8000/api/download/${jobId}`);
const blob = await response.blob();
const url = URL.createObjectURL(blob);

// Create download link
const a = document.createElement('a');
a.href = url;
a.download = 'processed-video.mp4';
a.click();
```

**Response:**
- Content-Type: `video/mp4`
- File download

---

### List All Jobs

**GET** `/api/jobs`

List all processing jobs, optionally filtered by status.

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `processing`, `completed`, `failed`)
- `limit` (optional): Maximum number of jobs to return (default: 50)

**Example:**
```bash
# Get all jobs
curl http://localhost:8000/api/jobs

# Get only completed jobs
curl http://localhost:8000/api/jobs?status=completed

# Get last 10 jobs
curl http://localhost:8000/api/jobs?limit=10
```

**Response:**
```json
[
  {
    "job_id": "a1b2c3d4",
    "status": "completed",
    "progress": 100,
    "created_at": "2026-02-11T21:30:00",
    "video_title": "my-awesome-video"
  },
  {
    "job_id": "e5f6g7h8",
    "status": "processing",
    "progress": 45,
    "created_at": "2026-02-11T21:35:00",
    "video_title": "another-video"
  }
]
```

---

### Delete Job

**DELETE** `/api/jobs/{job_id}`

Delete a job and its associated files.

**Parameters:**
- `job_id` (path parameter): The job ID

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/jobs/a1b2c3d4
```

**Response:**
```json
{
  "message": "Job deleted successfully"
}
```

**Note:** Cannot delete jobs that are currently processing.

---

## Processing Modes

### Continuous (Default)
- Extracts a single continuous 120-second segment
- Fastest processing time
- Best for quick highlights

### Multi-Segment
- Extracts 3-5 important segments from the entire video
- Stitches them together seamlessly
- Better content coverage
- Best for educational or tutorial content

### Scene-Based
- Detects visual scene boundaries
- Analyzes scene content with AI
- Selects most important scenes
- Best for presentations and demonstrations

---

## Error Responses

All endpoints return standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `413 Payload Too Large`: Uploaded file exceeds size limit
- `429 Too Many Requests`: Maximum concurrent jobs reached
- `500 Internal Server Error`: Server error

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Frontend Integration Example

### React Example

```javascript
import { useState, useEffect } from 'react';

function VideoProcessor() {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const API_URL = 'http://localhost:8000';

  // Submit a video for processing
  const processVideo = async (videoUrl) => {
    const response = await fetch(`${API_URL}/api/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_url: videoUrl,
        mode: 'multi_segment',
        add_subtitles: true
      })
    });
    
    const data = await response.json();
    setJobId(data.job_id);
  };

  // Poll for job status
  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      const response = await fetch(`${API_URL}/api/status/${jobId}`);
      const data = await response.json();
      setStatus(data);

      if (data.status === 'completed' || data.status === 'failed') {
        clearInterval(interval);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [jobId]);

  // Download the result
  const downloadVideo = async () => {
    const response = await fetch(`${API_URL}/api/download/${jobId}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'processed-video.mp4';
    a.click();
  };

  return (
    <div>
      <button onClick={() => processVideo('https://youtu.be/...')}>
        Process Video
      </button>
      
      {status && (
        <div>
          <p>Status: {status.status}</p>
          <p>Progress: {status.progress}%</p>
          <p>{status.message}</p>
          
          {status.status === 'completed' && (
            <button onClick={downloadVideo}>Download</button>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## CORS Configuration

The API is configured to accept requests from:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)

To add additional origins, update the `CORS_ORIGINS` variable in your `.env` file:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://yourdomain.com
```

---

## Limits and Constraints

- **Maximum Concurrent Jobs**: 3 (configurable via `MAX_CONCURRENT_JOBS`)
- **Maximum Upload Size**: 500MB (configurable via `UPLOAD_MAX_SIZE`)
- **Target Duration Range**: 30-300 seconds
- **Session Timeout**: Jobs are stored in memory and cleared on server restart

---

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to test endpoints directly from your browser.
