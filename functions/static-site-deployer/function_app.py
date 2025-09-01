"""
Azure Function: Static Site Deployer (Python)

Event-driven deployment of static sites from blob storage to Azure Static Web Apps.
Triggered when tar.gz site archives are uploaded to the static-sites container.
"""

import asyncio
import json
import logging
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import aiohttp
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StaticSiteDeployer:
    """Handles deployment of static sites to Azure Static Web Apps."""

    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.storage_account_url = os.environ.get("STORAGE_ACCOUNT_URL")
        self.static_app_name = os.environ.get("STATIC_WEB_APP_NAME")
        self.resource_group = os.environ.get("RESOURCE_GROUP_NAME")
        self.subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")

        if not all(
            [self.storage_account_url, self.static_app_name, self.resource_group]
        ):
            raise ValueError("Missing required environment variables")

        self.blob_client = BlobServiceClient(
            account_url=self.storage_account_url, credential=self.credential
        )

    async def deploy_site(self, blob_name: str, container_name: str) -> dict:
        """Deploy a static site from blob storage to Static Web Apps."""
        logger.info(f"Starting deployment for blob: {blob_name}")

        try:
            # Download and extract the site archive
            site_path = await self._download_and_extract(blob_name, container_name)

            # Get deployment token
            deployment_token = await self._get_deployment_token()

            # Deploy using SWA CLI
            await self._deploy_with_swa_cli(site_path, deployment_token)

            # Cleanup
            self._cleanup_temp_files(site_path.parent)

            logger.info(f"Successfully deployed {blob_name}")
            return {
                "status": "success",
                "blob_name": blob_name,
                "message": "Site deployed successfully",
            }

        except Exception as e:
            logger.error(f"Deployment failed for {blob_name}: {e}")
            raise

    async def _download_and_extract(self, blob_name: str, container_name: str) -> Path:
        """Download blob and extract to temporary directory."""
        logger.info(f"Downloading and extracting {blob_name}")

        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix="swa_deploy_"))
        archive_path = temp_dir / blob_name
        extract_path = temp_dir / "site"

        # Download blob
        blob_client = self.blob_client.get_blob_client(
            container=container_name, blob=blob_name
        )

        with open(archive_path, "wb") as f:
            download_stream = blob_client.download_blob()
            f.write(download_stream.readall())

        # Extract archive
        extract_path.mkdir()
        with tarfile.open(archive_path, "r:gz") as tar:
            # Security: validate paths before extraction
            for member in tar.getmembers():
                if not self._is_safe_path(member.name):
                    raise ValueError(f"Unsafe path in archive: {member.name}")
            tar.extractall(extract_path)

        # Remove archive file
        archive_path.unlink()

        logger.info(f"Extracted site to {extract_path}")
        return extract_path

    def _is_safe_path(self, path: str) -> bool:
        """Check if extraction path is safe (no directory traversal)."""
        return not (
            path.startswith("/") or path.startswith("\\") or ".." in path or ":" in path
        )

    async def _get_deployment_token(self) -> str:
        """Get deployment token for Static Web App."""
        logger.info("Retrieving Static Web App deployment token")

        # Get access token for Azure Resource Manager
        token = self.credential.get_token("https://management.azure.com/.default")

        # Call Azure Resource Manager API
        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.Web/staticSites/{self.static_app_name}"
            f"/listSecrets?api-version=2022-03-01"
        )

        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Failed to get deployment token: {response.status} - {error_text}"
                    )

                data = await response.json()
                deployment_token = data.get("properties", {}).get("deploymentToken")

                if not deployment_token:
                    raise Exception("Deployment token not found in response")

                logger.info("Successfully retrieved deployment token")
                return deployment_token

    async def _deploy_with_swa_cli(self, site_path: Path, deployment_token: str):
        """Deploy site using SWA CLI with secure argument handling."""
        logger.info("Starting SWA CLI deployment")

        # Install SWA CLI if not available (in function environment)
        await self._ensure_swa_cli()

        # Prepare deployment command with safe argument separation
        cmd = [
            "npx",
            "@azure/static-web-apps-cli",
            "deploy",
            str(site_path),
            "--deployment-token",
            deployment_token,
            "--env",
            "production",
        ]

        # Set up environment
        env = os.environ.copy()
        env["SWA_CLI_DEPLOYMENT_TOKEN"] = deployment_token

        logger.info("Executing SWA CLI deployment...")

        # Execute command safely
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=site_path,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise Exception(f"SWA CLI deployment failed: {error_msg}")

        logger.info("SWA CLI deployment completed successfully")
        logger.debug(f"SWA CLI output: {stdout.decode()}")

    async def _ensure_swa_cli(self):
        """Ensure SWA CLI is available."""
        try:
            # Check if SWA CLI is available
            process = await asyncio.create_subprocess_exec(
                "npx",
                "@azure/static-web-apps-cli",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            if process.returncode == 0:
                logger.info("SWA CLI is available")
                return
        except Exception:
            pass

        # Install SWA CLI
        logger.info("Installing SWA CLI...")
        process = await asyncio.create_subprocess_exec(
            "npm",
            "install",
            "-g",
            "@azure/static-web-apps-cli",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise Exception(f"Failed to install SWA CLI: {error_msg}")

        logger.info("SWA CLI installed successfully")

    def _cleanup_temp_files(self, temp_dir: Path):
        """Clean up temporary files."""
        try:
            import shutil

            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")


# Azure Function entry point
app = func.FunctionApp()


@app.blob_trigger(
    arg_name="myblob", path="static-sites/{name}", connection="AzureWebJobsStorage"
)
async def static_site_deployer(myblob: func.InputStream) -> None:
    """
    Azure Function triggered by blob uploads to static-sites container.
    Deploys static site archives to Azure Static Web Apps.
    """
    logger.info(f"Processing blob: {myblob.name}")

    try:
        # Extract container and blob name
        path_parts = myblob.name.split("/")
        if len(path_parts) < 2:
            logger.error(f"Invalid blob path: {myblob.name}")
            return

        container_name = path_parts[0]
        blob_name = "/".join(path_parts[1:])

        # Only process .tar.gz files
        if not blob_name.endswith(".tar.gz"):
            logger.info(f"Skipping non-archive file: {blob_name}")
            return

        # Deploy the site
        deployer = StaticSiteDeployer()
        result = await deployer.deploy_site(blob_name, container_name)

        logger.info(f"Deployment result: {result}")

    except Exception as e:
        logger.error(f"Function execution failed: {e}")
        # Don't re-raise in Azure Functions to avoid retries for non-transient errors
        # Azure Functions will log the error automatically
