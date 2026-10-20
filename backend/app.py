import os
import uuid
import time
import tempfile
import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from rppg_engine import analyze_video_rppg

app = FastAPI(title="SafeGuard rPPG Deepfake Detector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DDB_TABLE = os.environ.get("DDB_TABLE_NAME", "")

@app.get("/")
def root():
    return {
        "service": "SafeGuard rPPG Deepfake Detector",
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "safeguard-rppg"}

@app.post("/analyze")
async def analyze_video(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".mp4", ".mov", ".avi", ".webm")):
        raise HTTPException(status_code=400, detail="Unsupported video format.")

    with tempfile.NamedTemporaryFile(dir="/tmp" if os.path.exists("/tmp") else None, suffix=".mp4", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = analyze_video_rppg(tmp_path)
        result["scan_id"] = str(uuid.uuid4())
        result["timestamp"] = int(time.time())

        if DDB_TABLE:
            try:
                ddb = boto3.resource("dynamodb")
                table = ddb.Table(DDB_TABLE)
                table.put_item(Item={
                    "scan_id": result["scan_id"],
                    "timestamp": result["timestamp"],
                    "verdict": result["verdict"],
                    "bpm": str(result["estimated_bpm"]),
                    "coherence": str(result["spatial_coherence"]),
                    "snr_db": str(result["snr_db"])
                })
            except Exception as e:
                print(f"DynamoDB logging skipped/failed: {e}")

        return result
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# AWS Lambda entrypoint
handler = Mangum(app)
