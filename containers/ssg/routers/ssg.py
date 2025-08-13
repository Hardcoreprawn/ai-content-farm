"""
Static Site Generator Router

Handles markdown generation and static site publishing for processed content.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
import jinja2
import markdown
import yaml
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential


router = APIRouter(prefix="/api/ssg", tags=["static-site-generator"])


# Data Models
class ContentItem(BaseModel):
    """Individual content item for site generation"""
    id: str
    title: str
    content: str
    summary: str
    category: str
    sentiment: str
    tags: List[str]
    engagement_score: float
    monetization_score: float
    quality_score: float
    recency_score: float
    final_score: float
    source: str
    source_url: str
    created_at: str
    processed_at: str


class SiteConfig(BaseModel):
    """Site configuration for generation"""
    site_title: str = "AI Content Farm"
    site_description: str = "Curated content powered by AI"
    base_url: str = "https://example.com"
    theme: str = "default"
    posts_per_page: int = 10
    categories: List[str] = []
    output_format: str = "markdown"  # markdown, html, json


class GenerateJobRequest(BaseModel):
    """Request to generate static site"""
    config: SiteConfig
    content_source: str  # blob path or job_id
    output_destination: Optional[str] = None  # blob path for output
    template_source: Optional[str] = None  # custom templates


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    status: str  # pending, running, completed, failed
    created_at: str
    updated_at: str
    message: str
    output_location: Optional[str] = None
    error: Optional[str] = None


# In-memory job store (replace with database in production)
job_store: Dict[str, JobStatus] = {}


# Global services
blob_service_client = None


async def get_blob_service_client():
    """Get Azure Blob Storage client"""
    global blob_service_client
    if blob_service_client is None:
        try:
            # Try Azure credential first
            credential = DefaultAzureCredential()
            storage_account = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "aicontentfarm")
            blob_service_client = BlobServiceClient(
                account_url=f"https://{storage_account}.blob.core.windows.net",
                credential=credential
            )
        except Exception:
            # Fall back to connection string for local development
            connection_string = os.getenv(
                "AZURE_STORAGE_CONNECTION_STRING",
                "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;"
            )
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    return blob_service_client


async def load_content_data(source_path: str) -> List[ContentItem]:
    """Load content data from blob storage"""
    try:
        client = await get_blob_service_client()
        
        # Parse container and blob path
        parts = source_path.split('/', 1)
        container_name = parts[0]
        blob_name = parts[1] if len(parts) > 1 else ""
        
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)
        content = await blob_client.download_blob()
        data = json.loads(content.readall())
        
        # Convert to ContentItem objects
        items = []
        if isinstance(data, list):
            for item in data:
                items.append(ContentItem(**item))
        elif isinstance(data, dict) and 'items' in data:
            for item in data['items']:
                items.append(ContentItem(**item))
        
        return items
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load content: {str(e)}")


async def generate_markdown_files(content_items: List[ContentItem], config: SiteConfig) -> Dict[str, str]:
    """Generate markdown files for content items"""
    files = {}
    
    # Create index page
    index_content = f"# {config.site_title}\n\n{config.site_description}\n\n"
    index_content += "## Latest Content\n\n"
    
    # Sort by final score descending
    sorted_items = sorted(content_items, key=lambda x: x.final_score, reverse=True)
    
    for item in sorted_items[:config.posts_per_page]:
        index_content += f"- [{item.title}]({item.id}.md) - Score: {item.final_score:.2f}\n"
    
    files["index.md"] = index_content
    
    # Create individual content pages
    for item in content_items:
        content = f"""---
title: {item.title}
category: {item.category}
sentiment: {item.sentiment}
tags: {', '.join(item.tags)}
engagement_score: {item.engagement_score}
monetization_score: {item.monetization_score}
quality_score: {item.quality_score}
recency_score: {item.recency_score}
final_score: {item.final_score}
source: {item.source}
source_url: {item.source_url}
created_at: {item.created_at}
processed_at: {item.processed_at}
---

# {item.title}

## Summary
{item.summary}

## Content
{item.content}

---
*Source: [{item.source}]({item.source_url})*
*Final Score: {item.final_score:.2f}*
"""
        files[f"{item.id}.md"] = content
    
    # Create category pages
    categories = {}
    for item in content_items:
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append(item)
    
    for category, items in categories.items():
        category_content = f"# {category}\n\n"
        sorted_items = sorted(items, key=lambda x: x.final_score, reverse=True)
        
        for item in sorted_items:
            category_content += f"- [{item.title}]({item.id}.md) - Score: {item.final_score:.2f}\n"
        
        files[f"category_{category.lower().replace(' ', '_')}.md"] = category_content
    
    # Create site configuration file
    site_config = {
        "title": config.site_title,
        "description": config.site_description,
        "base_url": config.base_url,
        "theme": config.theme,
        "posts_per_page": config.posts_per_page,
        "categories": list(categories.keys()),
        "generated_at": datetime.utcnow().isoformat()
    }
    files["_config.yml"] = yaml.dump(site_config)
    
    return files


async def upload_generated_files(files: Dict[str, str], destination: str) -> str:
    """Upload generated files to blob storage"""
    try:
        client = await get_blob_service_client()
        
        # Parse destination
        parts = destination.split('/', 1)
        container_name = parts[0]
        blob_prefix = parts[1] if len(parts) > 1 else ""
        
        uploaded_files = []
        
        for filename, content in files.items():
            blob_name = f"{blob_prefix}/{filename}" if blob_prefix else filename
            blob_client = client.get_blob_client(container=container_name, blob=blob_name)
            
            await blob_client.upload_blob(content, overwrite=True)
            uploaded_files.append(blob_name)
        
        return f"Uploaded {len(uploaded_files)} files to {destination}"
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")


async def process_site_generation(job_id: str, request: GenerateJobRequest):
    """Background task to process site generation"""
    try:
        # Update job status
        job_store[job_id].status = "running"
        job_store[job_id].updated_at = datetime.utcnow().isoformat()
        job_store[job_id].message = "Loading content data..."
        
        # Load content data
        content_items = await load_content_data(request.content_source)
        
        job_store[job_id].message = f"Generating site for {len(content_items)} content items..."
        
        # Generate markdown files
        files = await generate_markdown_files(content_items, request.config)
        
        job_store[job_id].message = f"Generated {len(files)} files, uploading..."
        
        # Upload files
        destination = request.output_destination or f"generated-sites/{job_id}"
        upload_result = await upload_generated_files(files, destination)
        
        # Update job status
        job_store[job_id].status = "completed"
        job_store[job_id].updated_at = datetime.utcnow().isoformat()
        job_store[job_id].message = upload_result
        job_store[job_id].output_location = destination
        
    except Exception as e:
        # Update job status
        job_store[job_id].status = "failed"
        job_store[job_id].updated_at = datetime.utcnow().isoformat()
        job_store[job_id].error = str(e)
        job_store[job_id].message = f"Generation failed: {str(e)}"


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test blob storage connection
        client = await get_blob_service_client()
        # Simple operation to verify connection
        containers = client.list_containers(max_results=1)
        list(containers)  # Force evaluation
        
        return {
            "status": "healthy",
            "service": "ssg",
            "blob_storage": "connected",
            "active_jobs": len([j for j in job_store.values() if j.status in ["pending", "running"]])
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "ssg",
            "error": str(e)
        }


@router.post("/generate", response_model=JobStatus)
async def generate_site(request: GenerateJobRequest, background_tasks: BackgroundTasks):
    """Start static site generation job"""
    
    # Create job
    job_id = f"ssg_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    job_status = JobStatus(
        job_id=job_id,
        status="pending",
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        message="Site generation job created"
    )
    
    job_store[job_id] = job_status
    
    # Start background task
    background_tasks.add_task(process_site_generation, job_id, request)
    
    return job_status


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status"""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_store[job_id]


@router.get("/jobs", response_model=List[JobStatus])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Maximum number of jobs to return")
):
    """List all jobs"""
    jobs = list(job_store.values())
    
    if status:
        jobs = [j for j in jobs if j.status == status]
    
    # Sort by created_at descending
    jobs.sort(key=lambda x: x.created_at, reverse=True)
    
    return jobs[:limit]


@router.get("/preview/{job_id}")
async def preview_generated_site(job_id: str):
    """Preview generated site content"""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_store[job_id]
    
    if job.status != "completed" or not job.output_location:
        raise HTTPException(status_code=400, detail="Job not completed or no output available")
    
    try:
        client = await get_blob_service_client()
        
        # List files in output location
        parts = job.output_location.split('/', 1)
        container_name = parts[0]
        blob_prefix = parts[1] if len(parts) > 1 else ""
        
        blob_list = client.list_blobs(container_name, name_starts_with=blob_prefix)
        
        files = {}
        for blob in blob_list:
            blob_client = client.get_blob_client(container=container_name, blob=blob.name)
            content = await blob_client.download_blob()
            files[blob.name] = content.readall().decode('utf-8')
        
        return {
            "job_id": job_id,
            "output_location": job.output_location,
            "files": files,
            "file_count": len(files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load preview: {str(e)}")


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its output"""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_store[job_id]
    
    # Delete output files if they exist
    if job.output_location:
        try:
            client = await get_blob_service_client()
            
            parts = job.output_location.split('/', 1)
            container_name = parts[0]
            blob_prefix = parts[1] if len(parts) > 1 else ""
            
            blob_list = client.list_blobs(container_name, name_starts_with=blob_prefix)
            
            for blob in blob_list:
                blob_client = client.get_blob_client(container=container_name, blob=blob.name)
                await blob_client.delete_blob()
                
        except Exception as e:
            # Log error but don't fail the deletion
            pass
    
    # Remove from job store
    del job_store[job_id]
    
    return {"message": f"Job {job_id} deleted successfully"}
