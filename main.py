"""
LocalMind - Replit Version
Simplified for Replit deployment
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from pathlib import Path

# Create FastAPI app
app = FastAPI(title="LocalMind Replit")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (for frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mock database for Replit
MOCK_DOCUMENTS = []
MOCK_SEARCHES = []

class SearchRequest(BaseModel):
    query: str
    include_web: bool = False
    max_results: int = 10

class Document(BaseModel):
    id: str
    title: str
    content: str
    type: str
    metadata: dict

@app.get("/")
async def serve_frontend():
    """Serve the frontend"""
    # In production, serve the built React app
    # For now, return a simple HTML page
    return FileResponse("templates/index.html")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "LocalMind Replit is running"}

@app.post("/api/search")
async def search(request: SearchRequest):
    """Mock search endpoint"""
    # Simulate search results
    mock_results = [
        {
            "id": "1",
            "title": "Sample Document 1",
            "content": f"Content matching '{request.query}'...",
            "type": "pdf",
            "source": "local",
            "metadata": {"size": "2.4 MB", "modified": "2024-12-01"}
        },
        {
            "id": "2",
            "title": "Sample Document 2",
            "content": f"Another result for '{request.query}'...",
            "type": "docx",
            "source": "local",
            "metadata": {"size": "1.2 MB", "modified": "2024-12-02"}
        }
    ]
    
    # Add to search history
    MOCK_SEARCHES.append(request.query)
    
    return {
        "results": mock_results[:request.max_results],
        "total": len(mock_results),
        "query_analysis": {
            "intent": "search",
            "keywords": request.query.split(),
            "needs_web": request.include_web
        }
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Mock file upload"""
    # Save file info (not actual file due to Replit limitations)
    doc = {
        "id": str(len(MOCK_DOCUMENTS) + 1),
        "title": file.filename,
        "content": f"Content of {file.filename}",
        "type": file.filename.split(".")[-1],
        "metadata": {
            "size": f"{file.size / 1024:.1f} KB" if file.size else "Unknown",
            "uploaded": "Just now"
        }
    }
    
    MOCK_DOCUMENTS.append(doc)
    
    return {
        "message": "File uploaded successfully",
        "document": doc
    }

@app.get("/api/documents")
async def list_documents():
    """List all documents"""
    return {
        "documents": MOCK_DOCUMENTS,
        "total": len(MOCK_DOCUMENTS)
    }

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "total_documents": len(MOCK_DOCUMENTS),
        "total_searches": len(MOCK_SEARCHES),
        "storage_used": f"{len(MOCK_DOCUMENTS) * 2.5:.1f} MB",
        "model_status": "Simulated (Replit Mode)",
        "last_indexed": "Just now"
    }

if __name__ == "__main__":
    import uvicorn
    # Replit uses port from environment
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
