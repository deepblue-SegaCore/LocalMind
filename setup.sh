
#!/bin/bash
# LocalMind Replit Setup Script
# Run this in your Python Repl's Shell

echo "🚀 Setting up LocalMind on Replit..."
echo "=================================="

# Step 1: Install Python dependencies
echo "📦 Installing Python packages..."
pip install fastapi uvicorn python-multipart pydantic chromadb langchain duckduckgo-search aiofiles

# Step 2: Install Node.js in Python Repl
echo "📦 Installing Node.js in Python Repl..."
npm init -y

# Step 3: Create project structure
echo "📁 Creating project structure..."

# Create directories
mkdir -p backend/core backend/api backend/database
mkdir -p frontend-build
mkdir -p static/css static/js
mkdir -p documents/samples
mkdir -p templates

# Step 4: Create package.json for frontend build
cat > package.json << 'EOF'
{
  "name": "localmind-replit",
  "version": "1.0.0",
  "scripts": {
    "build-frontend": "cd frontend && npm run build && cp -r dist/* ../static/",
    "setup": "npm install",
    "start": "python main.py"
  },
  "dependencies": {
    "vite": "^5.0.11",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }
}
EOF

# Step 5: Create main.py for Replit (already exists, skip this step)
echo "✅ main.py already exists"

# Step 6: Create basic HTML template
cat > templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LocalMind - Replit</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        input[type="text"] {
            flex: 1;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            background: rgba(255, 255, 255, 0.9);
        }
        button {
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            background: #4CAF50;
            color: white;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #45a049;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .feature-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        .api-links {
            margin-top: 30px;
            text-align: center;
        }
        .api-links a {
            color: #FFD700;
            text-decoration: none;
            margin: 0 15px;
            font-weight: bold;
        }
        .api-links a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 LocalMind</h1>
        <p style="text-align: center; font-size: 1.2em; margin-bottom: 30px;">
            Personal Knowledge Assistant - Replit Edition
        </p>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search your documents..." />
            <button onclick="search()">Search</button>
        </div>
        
        <div class="features">
            <div class="feature-card">
                <h3>📄 Document Upload</h3>
                <p>Upload and index your documents for intelligent search</p>
                <input type="file" id="fileInput" style="margin-top: 10px;" />
                <button onclick="uploadFile()" style="margin-top: 10px; padding: 10px 20px;">Upload</button>
            </div>
            
            <div class="feature-card">
                <h3>🔍 Smart Search</h3>
                <p>AI-powered semantic search across your knowledge base</p>
                <div id="searchResults" style="margin-top: 10px; text-align: left;"></div>
            </div>
            
            <div class="feature-card">
                <h3>📊 Statistics</h3>
                <p>Track your knowledge base growth and usage</p>
                <div id="stats" style="margin-top: 10px; text-align: left;">
                    <button onclick="loadStats()" style="padding: 10px 20px;">Load Stats</button>
                </div>
            </div>
        </div>
        
        <div class="api-links">
            <a href="/api/health" target="_blank">Health Check</a>
            <a href="/api/documents" target="_blank">View Documents</a>
            <a href="/api/stats" target="_blank">API Stats</a>
        </div>
    </div>

    <script>
        async function search() {
            const query = document.getElementById('searchInput').value;
            if (!query) return;
            
            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        query: query,
                        include_web: false,
                        max_results: 5
                    })
                });
                
                const data = await response.json();
                const resultsDiv = document.getElementById('searchResults');
                
                if (data.results && data.results.length > 0) {
                    resultsDiv.innerHTML = '<h4>Results:</h4>' + 
                        data.results.map(result => 
                            `<div style="margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 5px;">
                                <strong>${result.title}</strong><br>
                                <small>${result.content}</small>
                            </div>`
                        ).join('');
                } else {
                    resultsDiv.innerHTML = '<p>No results found.</p>';
                }
            } catch (error) {
                console.error('Search error:', error);
                document.getElementById('searchResults').innerHTML = '<p>Search error occurred.</p>';
            }
        }
        
        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                alert('File uploaded successfully: ' + data.document.title);
                fileInput.value = '';
            } catch (error) {
                console.error('Upload error:', error);
                alert('Upload failed');
            }
        }
        
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('stats').innerHTML = `
                    <div style="text-align: left;">
                        <p><strong>Documents:</strong> ${data.total_documents}</p>
                        <p><strong>Searches:</strong> ${data.total_searches}</p>
                        <p><strong>Storage:</strong> ${data.storage_used}</p>
                        <p><strong>Status:</strong> ${data.model_status}</p>
                    </div>
                `;
            } catch (error) {
                console.error('Stats error:', error);
                document.getElementById('stats').innerHTML = '<p>Error loading stats</p>';
            }
        }
        
        // Allow Enter key to trigger search
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                search();
            }
        });
    </script>
</body>
</html>
EOF

# Step 7: Create basic CSS and JS files
cat > static/css/style.css << 'EOF'
/* Additional styles for LocalMind */
.loading {
    opacity: 0.6;
    pointer-events: none;
}

.success {
    color: #4CAF50;
}

.error {
    color: #f44336;
}
EOF

cat > static/js/app.js << 'EOF'
// Additional JavaScript for LocalMind functionality
console.log('LocalMind Replit loaded successfully');
EOF

# Step 8: Create sample documents
cat > documents/samples/welcome.txt << 'EOF'
Welcome to LocalMind!

This is a sample document to demonstrate the search functionality.
LocalMind is a personal knowledge assistant that helps you search through your documents using AI.

Features:
- Document upload and indexing
- Semantic search
- Web search integration
- Statistics and analytics

Try uploading your own documents and searching for specific topics!
EOF

cat > documents/samples/features.md << 'EOF'
# LocalMind Features

## Core Functionality
- **Document Processing**: Upload PDFs, Word docs, text files
- **Smart Search**: AI-powered semantic search
- **Web Integration**: Optional web search results
- **Real-time Indexing**: Documents are processed immediately

## Technical Stack
- FastAPI backend
- ChromaDB vector database
- LangChain for AI processing
- React frontend (in full version)

## Replit Adaptations
- Simplified file storage
- Mock database for demonstration
- Streamlined UI in single HTML file
- Environment-based configuration
EOF

echo "✅ Setup complete!"
echo ""
echo "🎉 LocalMind is now ready!"
echo "Click the 'Run' button to start the application."
echo ""
echo "Available endpoints:"
echo "  • / - Main interface"
echo "  • /api/health - Health check"
echo "  • /api/search - Search endpoint"
echo "  • /api/upload - File upload"
echo "  • /api/documents - List documents"
echo "  • /api/stats - System statistics"
