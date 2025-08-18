"""
Markdown to Static Site Converter

This container watches for markdown output from the markdown generator
and automatically converts it to a static website.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import asyncio
import httpx
import logging
from datetime import datetime, timezone
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Markdown to Static Site Converter",
    description="Converts markdown content to static websites",
    version="1.0.0"
)


class ConversionRequest(BaseModel):
    """Request to convert markdown to static site."""
    markdown_dir: str = "/app/output/markdown"
    output_dir: str = "/app/site"
    auto_publish: bool = True


class FileWatcher:
    """Watches for new markdown files and triggers conversion."""

    def __init__(self):
        self.watch_dir = "/app/output/markdown"
        self.last_check = datetime.now(timezone.utc)
        self.processed_files = set()

    async def start_watching(self):
        """Start watching for file changes."""
        logger.info(f"Starting file watcher on {self.watch_dir}")

        while True:
            try:
                await self.check_for_changes()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"File watcher error: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    async def check_for_changes(self):
        """Check for new or changed markdown files."""
        if not os.path.exists(self.watch_dir):
            return

        try:
            # Look for publishing manifest
            manifest_file = os.path.join(
                self.watch_dir, "publishing_manifest.json")

            if os.path.exists(manifest_file):
                # Check if manifest is newer than last check
                mtime = datetime.fromtimestamp(
                    os.path.getmtime(manifest_file), timezone.utc)

                if mtime > self.last_check and manifest_file not in self.processed_files:
                    logger.info(
                        f"New publishing manifest detected: {manifest_file}")
                    await self.trigger_conversion(manifest_file)
                    self.processed_files.add(manifest_file)
                    self.last_check = datetime.now(timezone.utc)

            # Also check for individual markdown files
            for md_file in Path(self.watch_dir).glob("*.md"):
                if md_file.name == "index.md":
                    continue  # Skip index file

                mtime = datetime.fromtimestamp(
                    md_file.stat().st_mtime, timezone.utc)

                if mtime > self.last_check and str(md_file) not in self.processed_files:
                    logger.info(f"New markdown file detected: {md_file}")
                    await self.trigger_single_file_conversion(str(md_file))
                    self.processed_files.add(str(md_file))

        except Exception as e:
            logger.error(f"Error checking for changes: {e}")

    async def trigger_conversion(self, manifest_file: str):
        """Trigger conversion when new manifest is detected."""
        try:
            # Call SSG service to generate site
            async with httpx.AsyncClient() as client:
                response = await client.get("http://ssg:8000/generate/sync", timeout=120.0)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Site generation completed: {result}")

                    # Notify that site is ready
                    await self.notify_site_ready(result)
                else:
                    logger.error(
                        f"Site generation failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Failed to trigger conversion: {e}")

    async def trigger_single_file_conversion(self, md_file: str):
        """Handle single file updates."""
        logger.info(f"Processing single markdown file: {md_file}")
        # For now, just trigger full site rebuild
        # Could be optimized to only update specific pages
        await self.trigger_conversion(md_file)

    async def notify_site_ready(self, generation_result: Dict[str, Any]):
        """Notify other services that the site is ready."""
        try:
            notification = {
                "event": "site_generated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": generation_result,
                "preview_url": "http://localhost:8005/preview/",
                "pages_generated": generation_result.get("result", {}).get("pages_generated", 0)
            }

            # Could send webhook notifications here
            logger.info(f"Site ready notification: {notification}")

            # Save notification for API consumers
            notifications_dir = "/app/output/notifications"
            os.makedirs(notifications_dir, exist_ok=True)

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            notification_file = os.path.join(
                notifications_dir, f"site_ready_{timestamp}.json")

            with open(notification_file, 'w') as f:
                json.dump(notification, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")


# Global file watcher instance
file_watcher = FileWatcher()


@app.on_event("startup")
async def startup_event():
    """Start the file watcher when the app starts."""
    asyncio.create_task(file_watcher.start_watching())


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Markdown to Static Site Converter",
        "version": "1.0.0",
        "status": "watching",
        "watch_directory": file_watcher.watch_dir,
        "last_check": file_watcher.last_check.isoformat(),
        "processed_files_count": len(file_watcher.processed_files)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "markdown-converter",
        "watching": True
    }


@app.post("/convert")
async def convert_markdown(request: ConversionRequest, background_tasks: BackgroundTasks):
    """Manually trigger markdown to static site conversion."""
    try:
        # Trigger conversion via SSG service
        async with httpx.AsyncClient() as client:
            response = await client.get("http://ssg:8000/generate/sync", timeout=120.0)

            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "conversion_completed",
                    "result": result,
                    "preview_url": "http://localhost:8005/preview/"
                }
            else:
                raise HTTPException(
                    status_code=500, detail="SSG service failed")

    except Exception as e:
        logger.error(f"Manual conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notifications")
async def get_notifications():
    """Get recent site generation notifications."""
    try:
        notifications_dir = "/app/output/notifications"

        if not os.path.exists(notifications_dir):
            return {"notifications": []}

        notifications = []
        for file in sorted(Path(notifications_dir).glob("site_ready_*.json"), reverse=True)[:10]:
            try:
                with open(file, 'r') as f:
                    notification = json.load(f)
                    notifications.append(notification)
            except Exception as e:
                logger.error(f"Failed to read notification {file}: {e}")

        return {"notifications": notifications}

    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        return {"notifications": [], "error": str(e)}


@app.get("/status")
async def get_status():
    """Get detailed status of the markdown converter."""
    try:
        # Check if SSG service is available
        ssg_available = False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://ssg:8000/health", timeout=5.0)
                ssg_available = response.status_code == 200
        except:
            pass

        # Get file statistics
        markdown_files = 0
        site_files = 0

        if os.path.exists("/app/output/markdown"):
            markdown_files = len(
                list(Path("/app/output/markdown").glob("*.md")))

        if os.path.exists("/app/site"):
            site_files = len(list(Path("/app/site").rglob("*")))

        return {
            "service": "markdown-converter",
            "status": "running",
            "file_watcher": {
                "watching": True,
                "watch_directory": file_watcher.watch_dir,
                "last_check": file_watcher.last_check.isoformat(),
                "processed_files": len(file_watcher.processed_files)
            },
            "ssg_service": {
                "available": ssg_available,
                "url": "http://ssg:8000"
            },
            "file_statistics": {
                "markdown_files": markdown_files,
                "site_files": site_files
            },
            "preview_url": "http://localhost:8005/preview/"
        }

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
