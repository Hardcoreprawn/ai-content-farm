import logging
import azure.functions as func
import praw
import json
import os
import uuid
import asyncio
import threading
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def update_job_status(blob_service_client, container_name, job_id, status, progress=None, error=None, results=None):
    """Update job status in blob storage"""
    try:
        status_blob_name = f"jobs/{job_id}/status.json"
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=status_blob_name
        )
        
        status_data = {
            "job_id": job_id,
            "status": status,  # "queued", "running", "completed", "failed"
            "updated_at": datetime.utcnow().isoformat(),
            "progress": progress,
            "error": error,
            "results": results
        }
        
        blob_client.upload_blob(
            json.dumps(status_data, indent=2),
            overwrite=True,
            content_type="application/json"
        )
        logging.info(f"📊 Job {job_id} status updated to: {status}")
        
    except Exception as e:
        logging.error(f"❌ Failed to update job status for {job_id}: {e}")


def process_reddit_data_async(job_id, source, subreddits, limit, blob_service_client, container_name, reddit_client_id, reddit_client_secret, reddit_user_agent):
    """Process Reddit data asynchronously"""
    try:
        # Update status to running
        update_job_status(blob_service_client, container_name, job_id, "running", 
                         progress={"step": "initializing", "completed": 0, "total": len(subreddits)})
        
        # Initialize Reddit API client (PRAW)
        try:
            reddit = praw.Reddit(
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent=reddit_user_agent
            )
            logging.info(f"✅ PRAW Reddit client initialized for job {job_id}")
        except Exception as e:
            logging.error(f"❌ Failed to initialize Reddit client for job {job_id}: {e}")
            update_job_status(blob_service_client, container_name, job_id, "failed", 
                            error=f"Reddit authentication failed: {str(e)}")
            return

        # Process subreddits
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        total_topics = 0
        results = []
        completed = 0

        for subreddit_name in subreddits:
            try:
                # Update progress
                update_job_status(blob_service_client, container_name, job_id, "running", 
                                progress={"step": f"processing r/{subreddit_name}", "completed": completed, "total": len(subreddits)})
                
                logging.info(f"🌐 Job {job_id}: Fetching hot topics from r/{subreddit_name}")
                
                # Use PRAW to get hot posts from subreddit
                subreddit = reddit.subreddit(subreddit_name)
                hot_posts = list(subreddit.hot(limit=limit))
                
                logging.info(f"📡 Job {job_id}: Successfully fetched {len(hot_posts)} posts from r/{subreddit_name}")

                # Extract detailed topic information
                topics = []
                for post in hot_posts:
                    # Get both external URL and Reddit discussion URL
                    external_url = post.url if hasattr(post, 'url') else ""
                    reddit_url = f"https://www.reddit.com{post.permalink}"
                    
                    topic = {
                        "title": post.title,
                        "external_url": external_url,
                        "reddit_url": reddit_url,
                        "reddit_id": post.id,
                        "score": post.score,
                        "created_utc": int(post.created_utc),
                        "num_comments": post.num_comments,
                        "author": str(post.author) if post.author else "",
                        "subreddit": subreddit_name,
                        "fetched_at": timestamp,
                        "selftext": post.selftext[:500] if hasattr(post, 'selftext') and post.selftext else ""
                    }
                    topics.append(topic)

                logging.info(f"📝 Job {job_id}: Processed {len(topics)} topics from r/{subreddit_name}")

                # Create individual file for each subreddit
                blob_data = {
                    "job_id": job_id,
                    "source": source,
                    "subject": subreddit_name,
                    "fetched_at": timestamp,
                    "count": len(topics),
                    "topics": topics
                }

                # Upload to Azure Storage
                blob_name = f"{timestamp}_{source}_{subreddit_name}.json"
                logging.info(f"📤 Job {job_id}: Attempting to upload to blob: {blob_name}")

                try:
                    blob_client = blob_service_client.get_blob_client(
                        container=container_name,
                        blob=blob_name
                    )

                    blob_client.upload_blob(
                        json.dumps(blob_data, indent=2),
                        overwrite=True,
                        content_type="application/json"
                    )
                    logging.info(f"✅ Job {job_id}: Successfully uploaded {len(topics)} topics from r/{subreddit_name} -> {blob_name}")
                    
                    results.append({
                        "subreddit": subreddit_name,
                        "topics_count": len(topics),
                        "blob_name": blob_name,
                        "status": "success"
                    })
                except Exception as blob_error:
                    logging.error(f"❌ Job {job_id}: Blob upload failed for r/{subreddit_name}: {blob_error}")
                    results.append({
                        "subreddit": subreddit_name,
                        "topics_count": len(topics),
                        "status": "upload_failed",
                        "error": str(blob_error)
                    })

                total_topics += len(topics)
                completed += 1

            except Exception as e:
                logging.error(f"❌ Job {job_id}: Failed to fetch topics from r/{subreddit_name}: {e}")
                results.append({
                    "subreddit": subreddit_name,
                    "status": "fetch_failed",
                    "error": str(e)
                })
                completed += 1

        # Prepare final results
        final_results = {
            "status": "completed",
            "timestamp": timestamp,
            "source": source,
            "total_topics": total_topics,
            "total_subreddits": len(subreddits),
            "results": results
        }

        # Update status to completed
        update_job_status(blob_service_client, container_name, job_id, "completed", 
                         progress={"step": "finished", "completed": completed, "total": len(subreddits)}, 
                         results=final_results)

        logging.info(f"🎉 Job {job_id}: Summary Wombles completed: {total_topics} total topics from {len(subreddits)} subreddits at {timestamp}")

    except Exception as e:
        logging.error(f"❌ Job {job_id}: Unexpected error in async processing: {e}")
        update_job_status(blob_service_client, container_name, job_id, "failed", 
                         error=f"Internal processing error: {str(e)}")


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('🚀 Summary Womble HTTP function started.')
    # Updated to support async job processing with job tickets - 2025-08-11

    try:
        # Parse request body
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Check if this is a status check request
        if req_body.get('action') == 'status':
            job_id = req_body.get('job_id')
            if not job_id:
                return func.HttpResponse(
                    json.dumps({"error": "job_id required for status check"}),
                    status_code=400,
                    mimetype="application/json"
                )
            
            # Get job status from blob storage
            try:
                # Initialize storage client for status check
                storage_account_name = os.environ.get("OUTPUT_STORAGE_ACCOUNT")
                container_name = os.environ.get("OUTPUT_CONTAINER", "hot-topics")
                
                if not storage_account_name:
                    return func.HttpResponse(
                        json.dumps({"error": "Storage account not configured"}),
                        status_code=500,
                        mimetype="application/json"
                    )
                
                credential = DefaultAzureCredential()
                blob_service_client = BlobServiceClient(
                    account_url=f"https://{storage_account_name}.blob.core.windows.net",
                    credential=credential
                )
                
                status_blob_name = f"jobs/{job_id}/status.json"
                blob_client = blob_service_client.get_blob_client(
                    container=container_name,
                    blob=status_blob_name
                )
                
                try:
                    blob_data = blob_client.download_blob().readall()
                    status_data = json.loads(blob_data.decode('utf-8'))
                    
                    return func.HttpResponse(
                        json.dumps(status_data, indent=2),
                        status_code=200,
                        mimetype="application/json"
                    )
                except Exception as e:
                    return func.HttpResponse(
                        json.dumps({"error": f"Job {job_id} not found or status unavailable", "details": str(e)}),
                        status_code=404,
                        mimetype="application/json"
                    )
                    
            except Exception as e:
                return func.HttpResponse(
                    json.dumps({"error": f"Failed to check job status: {str(e)}"}),
                    status_code=500,
                    mimetype="application/json"
                )

        # Generate unique job ID
        job_id = str(uuid.uuid4())
        logging.info(f"🎫 Generated job ticket: {job_id}")

        # Extract parameters with defaults
        source = req_body.get('source', 'reddit')
        subreddits = req_body.get('topics', [
            "technology", "programming", "MachineLearning", 
            "datascience", "computerscience", "gadgets", "Futurology"
        ])
        limit = req_body.get('limit', 10)
        credentials_config = req_body.get('credentials', {})
        storage_config = req_body.get('storage', {})

        logging.info(f"🔧 Job {job_id}: Source: {source}")
        logging.info(f"🔧 Job {job_id}: Topics: {subreddits}")
        logging.info(f"🔧 Job {job_id}: Limit: {limit}")

        # Validate required source
        if source != 'reddit':
            return func.HttpResponse(
                json.dumps({"error": f"Unsupported source: {source}"}),
                status_code=400,
                mimetype="application/json"
            )

        # Azure Storage configuration
        storage_account_name = storage_config.get('account_name') or os.environ.get("OUTPUT_STORAGE_ACCOUNT")
        container_name = storage_config.get('container_name') or os.environ.get("OUTPUT_CONTAINER", "hot-topics")

        if not storage_account_name:
            return func.HttpResponse(
                json.dumps({"error": "Storage account not configured"}),
                status_code=400,
                mimetype="application/json"
            )

        # Initialize storage client
        try:
            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(
                account_url=f"https://{storage_account_name}.blob.core.windows.net",
                credential=credential
            )
            logging.info("✅ Blob service client created successfully")
        except Exception as e:
            logging.error(f"❌ Failed to create blob service client: {e}")
            return func.HttpResponse(
                json.dumps({"error": f"Storage authentication failed: {str(e)}"}),
                status_code=500,
                mimetype="application/json"
            )

        # Get Reddit API credentials
        reddit_client_id = None
        reddit_client_secret = None
        reddit_user_agent = None

        # First try environment variables (from Function App settings with Key Vault references)
        reddit_client_id = os.environ.get("REDDIT_CLIENT_ID")
        reddit_client_secret = os.environ.get("REDDIT_CLIENT_SECRET") 
        reddit_user_agent = os.environ.get("REDDIT_USER_AGENT")

        if reddit_client_id and reddit_client_secret and reddit_user_agent:
            logging.info("✅ Retrieved Reddit credentials from environment variables")
        elif credentials_config.get('source') == 'keyvault':
            # Get from Key Vault
            try:
                key_vault_url = credentials_config.get('vault_url', f"https://aicontentstagingkvt0t36m.vault.azure.net")
                secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
                
                reddit_client_id = secret_client.get_secret(
                    credentials_config.get('client_id_secret', 'reddit-client-id')
                ).value
                reddit_client_secret = secret_client.get_secret(
                    credentials_config.get('client_secret_secret', 'reddit-client-secret')
                ).value
                
                logging.info("✅ Retrieved Reddit credentials from Key Vault")
            except Exception as e:
                logging.error(f"❌ Failed to retrieve credentials from Key Vault: {e}")
                return func.HttpResponse(
                    json.dumps({"error": f"Credential retrieval failed: {str(e)}"}),
                    status_code=500,
                    mimetype="application/json"
                )
        elif credentials_config.get('source') == 'direct':
            # Get from request (for testing)
            reddit_client_id = credentials_config.get('client_id')
            reddit_client_secret = credentials_config.get('client_secret')
            logging.info("✅ Using direct credentials from request")
        else:
            # Default: try Key Vault with environment defaults
            try:
                # Try to get Key Vault URL from environment, otherwise use default
                key_vault_url = os.environ.get("KEY_VAULT_URL", "https://aicontentstagingkvt0t36m.vault.azure.net")
                secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
                
                reddit_client_id = secret_client.get_secret("reddit-client-id").value
                reddit_client_secret = secret_client.get_secret("reddit-client-secret").value
                reddit_user_agent = secret_client.get_secret("reddit-user-agent").value
                
                logging.info("✅ Retrieved Reddit credentials from default Key Vault")
            except Exception as e:
                logging.error(f"❌ Failed to retrieve default credentials: {e}")
                return func.HttpResponse(
                    json.dumps({"error": f"No valid credentials configured: {str(e)}"}),
                    status_code=500,
                    mimetype="application/json"
                )

        if not reddit_client_id or not reddit_client_secret or not reddit_user_agent:
            logging.error(f"❌ Missing Reddit credentials - ID: {'✓' if reddit_client_id else '✗'}, Secret: {'✓' if reddit_client_secret else '✗'}, User Agent: {'✓' if reddit_user_agent else '✗'}")
            return func.HttpResponse(
                json.dumps({"error": "Reddit API credentials not properly configured"}),
                status_code=400,
                mimetype="application/json"
            )

        # Create initial job status
        update_job_status(blob_service_client, container_name, job_id, "queued", 
                         progress={"step": "initializing", "completed": 0, "total": len(subreddits)})

        # Start async processing in background thread
        try:
            thread = threading.Thread(
                target=process_reddit_data_async,
                args=(job_id, source, subreddits, limit, blob_service_client, container_name, 
                      reddit_client_id, reddit_client_secret, reddit_user_agent)
            )
            thread.daemon = True  # Dies when main thread dies
            thread.start()
            
            logging.info(f"� Job {job_id}: Background processing started for {len(subreddits)} subreddits")
            
        except Exception as e:
            logging.error(f"❌ Failed to start background processing for job {job_id}: {e}")
            update_job_status(blob_service_client, container_name, job_id, "failed", 
                             error=f"Failed to start processing: {str(e)}")
            return func.HttpResponse(
                json.dumps({"error": f"Failed to start background processing: {str(e)}"}),
                status_code=500,
                mimetype="application/json"
            )

        # Return job ticket immediately
        response_data = {
            "job_id": job_id,
            "status": "queued",
            "message": "Content processing started. Use job_id to check status.",
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "topics_requested": subreddits,
            "limit": limit,
            "status_check_example": {
                "method": "POST",
                "url": req.url,
                "body": {
                    "action": "status",
                    "job_id": job_id
                }
            }
        }

        logging.info(f"� Job {job_id}: Ticket issued for {len(subreddits)} subreddits")

        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=202,  # Accepted - processing started
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"❌ Unexpected error in Summary Womble: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )
