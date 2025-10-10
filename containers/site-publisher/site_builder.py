"""
Site builder orchestration for site-publisher.

Main composition function that orchestrates the complete build and deploy pipeline.
Individual operations are in content_downloader.py and hugo_builder.py.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from azure.storage.blob.aio import BlobServiceClient
from content_downloader import download_markdown_files, organize_content_for_hugo
from error_handling import handle_error
from hugo_builder import (
    backup_current_site,
    build_site_with_hugo,
    deploy_to_web_container,
    rollback_deployment,
)
from models import DeploymentResult
from security import sanitize_error_message

from config import Settings  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


async def build_and_deploy_site(
    blob_client: BlobServiceClient, config: Settings
) -> DeploymentResult:
    """
    Build and deploy static site (main composition function).

    This orchestrates the complete pipeline:
    1. Download markdown files from blob storage
    2. Organize content for Hugo
    3. Build site with Hugo
    4. Validate build output
    5. Deploy to $web container

    Args:
        blob_client: Azure blob service client (injected dependency)
        config: Application configuration (injected dependency)

    Returns:
        DeploymentResult with overall metrics and any errors
    """
    start_time = datetime.now()
    logger.info("Starting build and deploy pipeline")

    all_errors: List[str] = []

    try:
        # Step 1: Download markdown files
        temp_dir = Path("/tmp/site-builder")
        content_dir = temp_dir / "content"
        content_dir.mkdir(parents=True, exist_ok=True)

        download_result = await download_markdown_files(
            blob_client=blob_client,
            container_name=config.markdown_container,
            output_dir=content_dir,
        )

        if download_result.files_downloaded == 0:
            logger.error("No files downloaded, aborting pipeline")
            return DeploymentResult(
                files_uploaded=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=["No markdown files downloaded"] + download_result.errors,
            )

        all_errors.extend(download_result.errors)
        logger.info(f"Downloaded {download_result.files_downloaded} files")

        # Step 2: Organize content for Hugo
        hugo_dir = temp_dir / "hugo-site"
        hugo_content_dir = hugo_dir / "content"

        organize_result = await organize_content_for_hugo(
            content_dir=content_dir,
            hugo_content_dir=hugo_content_dir,
        )

        if not organize_result.is_valid:
            logger.error("Content organization failed, aborting pipeline")
            return DeploymentResult(
                files_uploaded=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=["Content organization failed"] + organize_result.errors,
            )

        all_errors.extend(organize_result.errors)

        # Step 3: Build site with Hugo
        config_file = Path(config.hugo_config_path)

        build_result = await build_site_with_hugo(
            hugo_dir=hugo_dir,
            config_file=config_file,
            base_url=config.hugo_base_url,
            timeout_seconds=config.build_timeout_seconds,
        )

        if not build_result.success:
            logger.error("Hugo build failed, aborting pipeline")
            return DeploymentResult(
                files_uploaded=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                errors=["Hugo build failed"] + build_result.errors,
            )

        all_errors.extend(build_result.errors)
        logger.info(f"Built site: {build_result.output_files} files")

        # Step 4: Backup current site (before deployment)
        backup_result = await backup_current_site(
            blob_client=blob_client,
            source_container=config.output_container,
            backup_container=config.backup_container,
        )

        # Note: Backup failures are logged but don't stop deployment
        if backup_result.errors:
            logger.warning(f"Backup completed with {len(backup_result.errors)} errors")
            all_errors.extend(backup_result.errors)
        else:
            logger.info(f"Backed up {backup_result.files_uploaded} files")

        # Step 5: Deploy to $web container
        public_dir = hugo_dir / "public"

        deploy_result = await deploy_to_web_container(
            blob_client=blob_client,
            source_dir=public_dir,
            container_name=config.output_container,
        )

        # If deployment failed catastrophically, attempt rollback
        if deploy_result.files_uploaded == 0 and backup_result.files_uploaded > 0:
            logger.error("Deployment failed completely - attempting rollback")

            rollback_result = await rollback_deployment(
                blob_client=blob_client,
                backup_container=config.backup_container,
                target_container=config.output_container,
            )

            if rollback_result.files_uploaded > 0:
                logger.warning(
                    f"Rollback successful: restored {rollback_result.files_uploaded} files"
                )
                all_errors.append("Deployment failed - rolled back to previous version")
            else:
                logger.error("Rollback failed - site may be in inconsistent state")
                all_errors.append("Deployment failed and rollback failed")

        all_errors.extend(deploy_result.errors)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Pipeline complete: {deploy_result.files_uploaded} files deployed in {duration:.2f}s"
        )

        return DeploymentResult(
            files_uploaded=deploy_result.files_uploaded,
            duration_seconds=duration,
            errors=all_errors,
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_info = handle_error(e, error_type="pipeline")
        return DeploymentResult(
            files_uploaded=0,
            duration_seconds=duration,
            errors=all_errors + [sanitize_error_message(e)],
        )
