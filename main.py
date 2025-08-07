
"""
Enhanced LocalMind for Replit
Adds real search functionality and document processing
within Replit's limitations
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
import asyncio
import aiofiles

# Simple vector store for Replit (no heavy dependencies)
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Create FastAPI app
app = FastAPI(
    title="LocalMind - Personal Knowledge Assistant",
    description="AI-powered document search system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize in-memory storage (for Replit)
class DocumentStore:
    def __init__(self):
        self.documents = {}
        self.search_history = []
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.document_vectors = None
        self.document_ids = []
        
    def add_document(self, doc_id: str, title: str, content: str, metadata: dict):
        """Add a document to the store"""
        self.documents[doc_id] = {
            "id": doc_id,
            "title": title,
            "content": content,
            "metadata": metadata,
            "added_at": datetime.now().isoformat()
        }
        # Rebuild vectors
        self._rebuild_vectors()
    
    def _rebuild_vectors(self):
        """Rebuild TF-IDF vectors for all documents"""
        if not self.documents:
            return
        
        texts = []
        self.document_ids = []
        
        for doc_id, doc in self.documents.items():
            texts.append(doc["content"])
            self.document_ids.append(doc_id)
        
        if texts:
            self.document_vectors = self.vectorizer.fit_transform(texts)
    
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search documents using TF-IDF similarity"""
        if not self.documents or self.document_vectors is None:
            return []
        
        # Add to search history
        self.search_history.append({
            "query": query,
            "timestamp": datetime.now().isoformat()
        })
        
        # Vectorize query
        query_vector = self.vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.document_vectors).flatten()
        
        # Get top results
        top_indices = similarities.argsort()[-max_results:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Only include if there's some similarity
                doc_id = self.document_ids[idx]
                doc = self.documents[doc_id].copy()
                doc["score"] = float(similarities[idx])
                results.append(doc)
        
        return results
    
    def get_stats(self) -> Dict:
        """Get storage statistics"""
        total_size = sum(
            len(doc["content"]) for doc in self.documents.values()
        )
        
        return {
            "total_documents": len(self.documents),
            "total_searches": len(self.search_history),
            "storage_used_kb": total_size / 1024,
            "unique_terms": len(self.vectorizer.vocabulary_) if hasattr(self.vectorizer, 'vocabulary_') else 0,
            "recent_searches": self.search_history[-5:][::-1] if self.search_history else []
        }

# Initialize document store
doc_store = DocumentStore()

# Models for API
class SearchRequest(BaseModel):
    query: str
    include_web: bool = False
    max_results: int = 10
    filters: Optional[Dict[str, Any]] = None

class DocumentUpload(BaseModel):
    title: str
    content: str
    type: str
    metadata: Optional[Dict[str, Any]] = {}

# Simulated document processor for different file types
class SimpleDocumentProcessor:
    """Simple document processor for Replit"""
    
    @staticmethod
    async def process_text_file(file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process plain text files"""
        try:
            content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content = file_content.decode('latin-1')
            except:
                content = file_content.decode('utf-8', errors='replace')
        
        # Validate content
        if not content.strip():
            raise ValueError("File appears to be empty or contains no readable text")
        
        return {
            "title": filename,
            "content": content,
            "type": "text",
            "metadata": {
                "filename": filename,
                "size_bytes": len(file_content),
                "line_count": len(content.split('\n')),
                "char_count": len(content)
            }
        }
    
    @staticmethod
    async def process_json_file(file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process JSON files"""
        try:
            data = json.loads(file_content.decode('utf-8'))
            # Convert JSON to searchable text
            content = json.dumps(data, indent=2)
            
            return {
                "title": filename,
                "content": content,
                "type": "json",
                "metadata": {
                    "filename": filename,
                    "size_bytes": len(file_content),
                    "keys": list(data.keys()) if isinstance(data, dict) else []
                }
            }
        except Exception as e:
            raise ValueError(f"Invalid JSON file: {e}")
    
    @staticmethod
    async def process_markdown_file(file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process Markdown files"""
        content = file_content.decode('utf-8')
        
        # Extract headers for better search
        headers = []
        for line in content.split('\n'):
            if line.startswith('#'):
                headers.append(line.strip('# ').strip())
        
        return {
            "title": filename,
            "content": content,
            "type": "markdown",
            "metadata": {
                "filename": filename,
                "size_bytes": len(file_content),
                "headers": headers[:5]  # First 5 headers
            }
        }
    
    @classmethod
    async def process_file(cls, file: UploadFile) -> Dict[str, Any]:
        """Process uploaded file based on type"""
        content = await file.read()
        filename = file.filename
        
        # Determine file type and process accordingly
        if filename.endswith('.txt'):
            return await cls.process_text_file(content, filename)
        elif filename.endswith('.json'):
            return await cls.process_json_file(content, filename)
        elif filename.endswith('.md'):
            return await cls.process_markdown_file(content, filename)
        else:
            # Default: treat as text
            return await cls.process_text_file(content, filename)

processor = SimpleDocumentProcessor()

# Mount static files (for frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# API Endpoints
@app.get("/")
async def home():
    """Serve the enhanced home page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LocalMind - Replit Edition</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-purple-600 to-blue-600 min-h-screen">
        <div class="container mx-auto p-8">
            <h1 class="text-4xl font-bold text-white text-center mb-4">
                🧠 LocalMind
            </h1>
            <p class="text-white text-center mb-8 text-lg">
                Personal Knowledge Assistant - Enhanced Replit Edition
            </p>
            
            <!-- Search Section -->
            <div class="bg-white rounded-lg shadow-xl p-6 mb-8">
                <div class="flex gap-4 mb-4">
                    <input type="text" id="searchInput" 
                           placeholder="Search your documents..."
                           class="flex-1 p-3 border rounded-lg focus:ring-2 focus:ring-blue-500">
                    <button onclick="search()" 
                            class="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 transition">
                        🔍 Search
                    </button>
                </div>
                <div class="flex gap-2 text-sm">
                    <label class="flex items-center">
                        <input type="checkbox" id="includeWeb" class="mr-1">
                        Include web results (simulated)
                    </label>
                </div>
            </div>
            
            <!-- Upload Section -->
            <div class="bg-white rounded-lg shadow-xl p-6 mb-8">
                <h3 class="text-xl font-bold mb-4">📁 Upload Documents</h3>
                <div class="flex gap-4 items-center">
                    <input type="file" id="fileInput" multiple accept=".txt,.json,.md"
                           class="flex-1 p-2 border rounded-lg">
                    <button onclick="uploadFiles()" 
                            class="bg-green-500 text-white px-6 py-3 rounded-lg hover:bg-green-600 transition">
                        📤 Upload
                    </button>
                </div>
                <p class="text-sm text-gray-600 mt-2">
                    Supported formats: .txt, .json, .md (Max 10MB per file)
                </p>
            </div>
            
            <!-- Results Section -->
            <div id="results" class="space-y-4"></div>
            
            <!-- Stats Section -->
            <div class="bg-white rounded-lg shadow-xl p-6 mt-8">
                <h3 class="text-xl font-bold mb-4">📊 Statistics</h3>
                <button onclick="loadStats()" 
                        class="bg-purple-500 text-white px-4 py-2 rounded-lg hover:bg-purple-600 transition mb-4">
                    🔄 Refresh Stats
                </button>
                <div id="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4"></div>
            </div>
            
            <!-- Documents List -->
            <div class="bg-white rounded-lg shadow-xl p-6 mt-8">
                <h3 class="text-xl font-bold mb-4">📚 Your Documents</h3>
                <button onclick="loadDocuments()" 
                        class="bg-indigo-500 text-white px-4 py-2 rounded-lg hover:bg-indigo-600 transition mb-4">
                    📋 List Documents
                </button>
                <div id="documents" class="space-y-2"></div>
            </div>
        </div>
        
        <script>
            async function search() {
                const query = document.getElementById('searchInput').value;
                const includeWeb = document.getElementById('includeWeb').checked;
                
                if (!query.trim()) {
                    alert('Please enter a search query');
                    return;
                }
                
                try {
                    const response = await fetch('/api/search', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            query: query,
                            include_web: includeWeb,
                            max_results: 10
                        })
                    });
                    
                    const data = await response.json();
                    
                    const resultsDiv = document.getElementById('results');
                    if (data.results && data.results.length > 0) {
                        resultsDiv.innerHTML = `
                            <h3 class="text-2xl font-bold text-white mb-4">🔍 Search Results (${data.total})</h3>
                            ${data.results.map(r => `
                                <div class="bg-white rounded-lg p-4 shadow hover:shadow-lg transition">
                                    <h4 class="font-bold text-lg mb-2">${r.title}</h4>
                                    <p class="text-gray-600 mb-2">${r.content.substring(0, 300)}...</p>
                                    <div class="flex justify-between items-center text-sm text-gray-500">
                                        <span>Type: ${r.type || r.metadata?.type || 'Unknown'}</span>
                                        <span>Score: ${(r.score || 0).toFixed(3)}</span>
                                    </div>
                                </div>
                            `).join('')}
                        `;
                    } else {
                        resultsDiv.innerHTML = `
                            <div class="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded">
                                <p class="font-bold">No results found</p>
                                <p>Try different keywords or upload some documents first.</p>
                            </div>
                        `;
                    }
                } catch (error) {
                    console.error('Search error:', error);
                    document.getElementById('results').innerHTML = `
                        <div class="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded">
                            <p class="font-bold">Search Error</p>
                            <p>${error.message}</p>
                        </div>
                    `;
                }
            }
            
            async function uploadFiles() {
                const fileInput = document.getElementById('fileInput');
                const files = fileInput.files;
                
                if (files.length === 0) {
                    alert('Please select files to upload');
                    return;
                }
                
                // Validate files before upload
                const maxSize = 5 * 1024 * 1024; // 5MB
                const allowedTypes = ['.txt', '.json', '.md'];
                
                for (let file of files) {
                    if (file.size > maxSize) {
                        alert(`File "${file.name}" is too large (max 5MB)`);
                        return;
                    }
                    
                    const ext = '.' + file.name.split('.').pop().toLowerCase();
                    if (!allowedTypes.includes(ext)) {
                        alert(`File "${file.name}" has unsupported type. Allowed: ${allowedTypes.join(', ')}`);
                        return;
                    }
                }
                
                const formData = new FormData();
                for (let file of files) {
                    formData.append('files', file);
                }
                
                try {
                    const response = await fetch('/api/bulk_upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Upload failed');
                    }
                    
                    const data = await response.json();
                    
                    let message = `✅ Uploaded: ${data.total_processed} files`;
                    if (data.total_failed > 0) {
                        message += `\n❌ Failed: ${data.total_failed} files`;
                        if (data.failed.length > 0) {
                            message += '\n\nErrors:';
                            data.failed.forEach(f => {
                                message += `\n• ${f.filename}: ${f.error}`;
                            });
                        }
                    }
                    alert(message);
                    
                    fileInput.value = '';
                    loadStats();
                    loadDocuments();
                } catch (error) {
                    console.error('Upload error:', error);
                    alert('Upload failed: ' + error.message);
                }
            }
            
            async function loadStats() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    
                    document.getElementById('stats').innerHTML = `
                        <div class="text-center">
                            <div class="text-2xl font-bold text-blue-600">${data.total_documents}</div>
                            <div class="text-sm text-gray-600">Documents</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-green-600">${data.total_searches}</div>
                            <div class="text-sm text-gray-600">Searches</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-purple-600">${Math.round(data.storage_used_kb)}</div>
                            <div class="text-sm text-gray-600">KB Used</div>
                        </div>
                        <div class="text-center">
                            <div class="text-2xl font-bold text-orange-600">${data.unique_terms}</div>
                            <div class="text-sm text-gray-600">Unique Terms</div>
                        </div>
                    `;
                } catch (error) {
                    console.error('Stats error:', error);
                }
            }
            
            async function loadDocuments() {
                try {
                    const response = await fetch('/api/documents');
                    const data = await response.json();
                    
                    const docsDiv = document.getElementById('documents');
                    if (data.documents && data.documents.length > 0) {
                        docsDiv.innerHTML = data.documents.map(doc => `
                            <div class="flex justify-between items-center p-3 bg-gray-50 rounded">
                                <div>
                                    <span class="font-medium">${doc.title}</span>
                                    <span class="text-sm text-gray-500 ml-2">(${doc.metadata?.filename || doc.type})</span>
                                </div>
                                <button onclick="deleteDocument('${doc.id}')" 
                                        class="text-red-500 hover:text-red-700">
                                    🗑️ Delete
                                </button>
                            </div>
                        `).join('');
                    } else {
                        docsDiv.innerHTML = '<p class="text-gray-500">No documents uploaded yet.</p>';
                    }
                } catch (error) {
                    console.error('Documents error:', error);
                }
            }
            
            async function deleteDocument(docId) {
                if (!confirm('Are you sure you want to delete this document?')) return;
                
                try {
                    const response = await fetch(`/api/documents/${docId}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        loadDocuments();
                        loadStats();
                    }
                } catch (error) {
                    console.error('Delete error:', error);
                }
            }
            
            // Allow Enter key to trigger search
            document.getElementById('searchInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    search();
                }
            });
            
            // Load initial stats
            loadStats();
        </script>
    </body>
    </html>
    """)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "LocalMind Enhanced Replit is running",
        "version": "1.0.0",
        "documents_loaded": len(doc_store.documents),
        "features": ["TF-IDF Search", "Document Processing", "Multi-format Support"]
    }

@app.post("/api/search")
async def search(request: SearchRequest):
    """Enhanced search endpoint with TF-IDF"""
    try:
        # Perform search
        results = doc_store.search(request.query, request.max_results)
        
        # Add mock web results if requested
        if request.include_web:
            web_results = [
                {
                    "title": f"Web: {request.query} - Building Standards",
                    "content": f"Latest building codes and standards for {request.query}...",
                    "type": "web",
                    "source": "web",
                    "url": "https://example.com/standards",
                    "score": 0.8
                }
            ]
            results.extend(web_results)
        
        return {
            "results": results,
            "total": len(results),
            "query_analysis": {
                "original_query": request.query,
                "terms": request.query.lower().split(),
                "search_type": "semantic" if len(doc_store.documents) > 0 else "keyword"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Enhanced file upload with processing"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        # Read file content first to check size
        content = await file.read()
        file_size = len(content)
        
        # Check file size (Replit limitation - 5MB for stability)
        if file_size > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 5MB)")
        
        # Check if file is empty
        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Validate file extension
        allowed_extensions = ['.txt', '.json', '.md']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=415, 
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Reset file position and process
        await file.seek(0)
        processed = await processor.process_file(file)
        
        # Generate document ID
        doc_id = hashlib.md5(f"{file.filename}{datetime.now()}".encode()).hexdigest()[:12]
        
        # Add to store
        doc_store.add_document(
            doc_id=doc_id,
            title=processed["title"],
            content=processed["content"],
            metadata=processed["metadata"]
        )
        
        return {
            "message": "File processed and indexed successfully",
            "document": {
                "id": doc_id,
                "title": processed["title"],
                "type": processed["type"],
                "metadata": processed["metadata"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/documents")
async def list_documents(skip: int = 0, limit: int = 50):
    """List all indexed documents"""
    docs = list(doc_store.documents.values())
    
    # Sort by added_at (newest first)
    docs.sort(key=lambda x: x.get("added_at", ""), reverse=True)
    
    return {
        "documents": docs[skip:skip+limit],
        "total": len(docs),
        "skip": skip,
        "limit": limit
    }

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document"""
    if doc_id not in doc_store.documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    del doc_store.documents[doc_id]
    doc_store._rebuild_vectors()
    
    return {"message": f"Document {doc_id} deleted successfully"}

@app.get("/api/stats")
async def get_stats():
    """Get enhanced statistics"""
    stats = doc_store.get_stats()
    
    # Add system info
    stats.update({
        "platform": "Replit",
        "model_status": "TF-IDF (Enhanced Mode)",
        "max_upload_size_mb": 10,
        "supported_formats": [".txt", ".json", ".md"],
        "features_available": {
            "semantic_search": True,
            "document_upload": True,
            "web_search": False,  # Simulated only
            "gpt_integration": False,  # Not available on Replit
            "ocr": False  # Not available on Replit
        }
    })
    
    return stats

@app.post("/api/bulk_upload")
async def bulk_upload(files: List[UploadFile] = File(...)):
    """Upload multiple files at once"""
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Limit number of files for Replit
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Too many files (max 10 at once)")
    
    results = []
    errors = []
    
    for file in files:
        try:
            # Skip if no filename
            if not file.filename:
                errors.append({
                    "filename": "unknown",
                    "status": "error",
                    "error": "No filename provided"
                })
                continue
            
            # Check file size first
            content = await file.read()
            if len(content) > 5 * 1024 * 1024:  # 5MB limit
                errors.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": "File too large (max 5MB)"
                })
                continue
            
            if len(content) == 0:
                errors.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": "File is empty"
                })
                continue
            
            # Reset file position
            await file.seek(0)
            
            # Process each file
            processed = await processor.process_file(file)
            doc_id = hashlib.md5(f"{file.filename}{datetime.now()}".encode()).hexdigest()[:12]
            
            doc_store.add_document(
                doc_id=doc_id,
                title=processed["title"],
                content=processed["content"],
                metadata=processed["metadata"]
            )
            
            results.append({
                "filename": file.filename,
                "status": "success",
                "doc_id": doc_id,
                "size_kb": round(len(content) / 1024, 2)
            })
        except Exception as e:
            errors.append({
                "filename": file.filename or "unknown",
                "status": "error",
                "error": str(e)
            })
    
    return {
        "successful": results,
        "failed": errors,
        "total_processed": len(results),
        "total_failed": len(errors),
        "message": f"Processed {len(results)} files successfully, {len(errors)} failed"
    }

# Add sample documents on startup
@app.on_event("startup")
async def startup_event():
    """Add sample documents for testing"""
    sample_docs = [
        {
            "id": "sample1",
            "title": "Construction Safety Guidelines",
            "content": """
            Construction Safety Guidelines
            
            1. Personal Protective Equipment (PPE)
            All workers must wear appropriate PPE including hard hats, safety glasses,
            and steel-toed boots. High-visibility vests are required in all active work areas.
            
            2. Fall Protection
            Fall protection is required when working at heights above 6 feet.
            Use guardrails, safety nets, or personal fall arrest systems.
            
            3. Electrical Safety
            Lock out/tag out procedures must be followed. Only qualified electricians
            should work on electrical systems. Ground fault circuit interrupters (GFCI)
            required for all temporary power.
            
            4. Excavation Safety
            Trenches deeper than 5 feet require protective systems. Daily inspections
            by competent person required. Keep heavy equipment away from trench edges.
            """,
            "metadata": {
                "type": "safety",
                "category": "guidelines",
                "date": "2024-01-15"
            }
        },
        {
            "id": "sample2",
            "title": "Concrete Specifications",
            "content": """
            Concrete Mix Design Specifications
            
            Standard Structural Concrete:
            - Minimum compressive strength: 3000 PSI at 28 days
            - Maximum water-cement ratio: 0.50
            - Minimum cement content: 520 lbs/cubic yard
            - Air entrainment: 5-7% for exterior exposure
            
            High-Strength Concrete:
            - Compressive strength: 5000-8000 PSI
            - Water-cement ratio: 0.35-0.40
            - Include silica fume or fly ash for improved strength
            - Curing: Maintain moisture for minimum 7 days
            
            Testing Requirements:
            - Slump test for each truck
            - Compression test cylinders: 1 set per 50 cubic yards
            - Test at 7 and 28 days
            """,
            "metadata": {
                "type": "specification",
                "category": "concrete",
                "date": "2024-02-20"
            }
        },
        {
            "id": "sample3",
            "title": "Electrical System Layout",
            "content": """
            Building A - Electrical Distribution System
            
            Main Electrical Room (MER):
            - Location: Ground floor, Grid A-1
            - Main switchboard: 2000A, 480V, 3-phase
            - Emergency generator: 500kW diesel backup
            - UPS system: 100kVA for critical loads
            
            Distribution:
            Floor 1: Panel LP-1A (Grid B-2) - 225A for lighting
                    Panel PP-1A (Grid C-3) - 400A for power
            Floor 2: Panel LP-2A (Grid B-2) - 225A for lighting
                    Panel PP-2A (Grid C-3) - 400A for power
            
            Emergency Systems:
            - Exit lighting on emergency circuits
            - Fire alarm system on dedicated circuit with battery backup
            - Elevator power with automatic transfer switch
            """,
            "metadata": {
                "type": "drawing",
                "category": "electrical",
                "building": "A",
                "date": "2024-03-10"
            }
        }
    ]
    
    # Add sample documents to store
    for doc in sample_docs:
        doc_store.add_document(
            doc_id=doc["id"],
            title=doc["title"],
            content=doc["content"],
            metadata=doc["metadata"]
        )
    
    print(f"✅ Loaded {len(sample_docs)} sample documents")

# Replit-specific configuration
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
