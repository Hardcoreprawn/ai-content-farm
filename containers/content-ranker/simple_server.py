"""
Simple FastAPI test for content-ranker without external dependencies
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Minimal HTTP server for testing
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socketserver

# Import our core functions
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.ranking_engine import process_content_ranking

# Default config
DEFAULT_CONFIG = {
    'min_score_threshold': 100,
    'min_comments_threshold': 10,
    'weights': {
        'engagement': 0.3,
        'recency': 0.2,
        'monetization': 0.3,
        'title_quality': 0.2
    }
}

# In-memory job storage
job_storage = {}

def update_job_status(job_id: str, status: str, results: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    """Update job status"""
    job_storage[job_id] = {
        "job_id": job_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        "results": results,
        "error": error
    }

class ContentRankerHandler(BaseHTTPRequestHandler):
    def _send_json_response(self, data: dict, status_code: int = 200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def do_GET(self):
        """Handle GET requests"""
        path = urlparse(self.path).path
        
        if path == '/':
            self._send_json_response({
                "service": "AI Content Farm - Content Ranker API",
                "version": "2.0.0",
                "status": "healthy",
                "architecture": "container-apps",
                "available_endpoints": {
                    "content_ranking": "/api/content-ranker/",
                    "health_checks": "/health",
                    "documentation": "/docs"
                }
            })
        elif path == '/health' or path == '/api/content-ranker/health':
            self._send_json_response({
                "status": "healthy",
                "service": "content-ranker",
                "timestamp": datetime.utcnow().isoformat()
            })
        elif path == '/api/content-ranker/docs':
            self._send_json_response({
                "service": "Content Ranker Service",
                "version": "2.0.0",
                "description": "Rank content topics using configurable algorithms",
                "endpoints": {
                    "POST /api/content-ranker/process": "Create ranking job",
                    "POST /api/content-ranker/status": "Check job status",
                    "GET /api/content-ranker/health": "Health check"
                },
                "example_request": {
                    "content_data": {
                        "topics": [
                            {
                                "title": "Sample Topic",
                                "score": 1500,
                                "num_comments": 50,
                                "created_utc": 1723521600
                            }
                        ]
                    }
                }
            })
        else:
            self._send_json_response({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests"""
        path = urlparse(self.path).path
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request_data = json.loads(post_data.decode())
        except json.JSONDecodeError:
            self._send_json_response({"error": "Invalid JSON"}, 400)
            return

        if path == '/api/content-ranker/process':
            self._handle_process_request(request_data)
        elif path == '/api/content-ranker/status':
            self._handle_status_request(request_data)
        else:
            self._send_json_response({"error": "Not found"}, 404)

    def _handle_process_request(self, request_data: dict):
        """Handle content ranking process request"""
        job_id = str(uuid.uuid4())
        
        try:
            # Validate request
            if 'content_data' not in request_data:
                self._send_json_response({
                    "error": "content_data is required"
                }, 400)
                return

            # Process ranking
            content_data = request_data['content_data']
            ranking_config = request_data.get('ranking_config', DEFAULT_CONFIG)
            
            # Merge with defaults
            config = {**DEFAULT_CONFIG}
            config.update(ranking_config)
            
            # Process using our pure functions
            result = process_content_ranking(content_data, config)
            
            # Update job status
            update_job_status(job_id, "completed", results=result)
            
            # Return job response
            self._send_json_response({
                "job_id": job_id,
                "status": "completed",
                "message": "Content ranking completed",
                "timestamp": datetime.utcnow().isoformat(),
                "request_type": "direct_content",
                "status_check_example": {
                    "method": "POST",
                    "url": "/api/content-ranker/status",
                    "body": {
                        "action": "status",
                        "job_id": job_id
                    }
                }
            })
            
        except Exception as e:
            update_job_status(job_id, "failed", error=str(e))
            self._send_json_response({
                "error": f"Processing failed: {str(e)}"
            }, 500)

    def _handle_status_request(self, request_data: dict):
        """Handle job status request"""
        if request_data.get('action') != 'status':
            self._send_json_response({
                "error": "Only 'status' action is supported"
            }, 400)
            return
            
        job_id = request_data.get('job_id')
        if not job_id:
            self._send_json_response({
                "error": "job_id is required"
            }, 400)
            return
            
        job_data = job_storage.get(job_id)
        if not job_data:
            self._send_json_response({
                "error": f"Job {job_id} not found"
            }, 404)
            return
            
        self._send_json_response(job_data)

if __name__ == "__main__":
    PORT = 8001
    with socketserver.TCPServer(("", PORT), ContentRankerHandler) as httpd:
        print(f"Content Ranker API running on http://localhost:{PORT}")
        print(f"Health check: http://localhost:{PORT}/health")
        print(f"Documentation: http://localhost:{PORT}/api/content-ranker/docs")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()