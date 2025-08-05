import logging
import azure.functions as func
import praw
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('🚀 Summary Womble HTTP function started.')

    try:
        # Parse request body
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Extract parameters with defaults
        source = req_body.get('source', 'reddit')
        subreddits = req_body.get('topics', [
            "technology", "programming", "MachineLearning", 
            "datascience", "computerscience", "gadgets", "Futurology"
        ])
        limit = req_body.get('limit', 10)
        credentials_config = req_body.get('credentials', {})
        storage_config = req_body.get('storage', {})

        logging.info(f"🔧 Source: {source}")
        logging.info(f"🔧 Topics: {subreddits}")
        logging.info(f"🔧 Limit: {limit}")

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

        if credentials_config.get('source') == 'keyvault':
            # Get from Key Vault
            try:
                key_vault_url = credentials_config.get('vault_url', f"https://hottopicskvib91ea.vault.azure.net")
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
                key_vault_url = f"https://hottopicskvib91ea.vault.azure.net"
                secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
                
                reddit_client_id = secret_client.get_secret("reddit-client-id").value
                reddit_client_secret = secret_client.get_secret("reddit-client-secret").value
                
                logging.info("✅ Retrieved Reddit credentials from default Key Vault")
            except Exception as e:
                logging.error(f"❌ Failed to retrieve default credentials: {e}")
                return func.HttpResponse(
                    json.dumps({"error": f"No valid credentials configured: {str(e)}"}),
                    status_code=500,
                    mimetype="application/json"
                )

        if not reddit_client_id or not reddit_client_secret:
            return func.HttpResponse(
                json.dumps({"error": "Reddit credentials not found"}),
                status_code=400,
                mimetype="application/json"
            )

        # Initialize Reddit API client (PRAW)
        try:
            reddit = praw.Reddit(
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent="Summary Wombles/1.0 by AI Content Farm"
            )
            logging.info("✅ PRAW Reddit client initialized successfully")
        except Exception as e:
            logging.error(f"❌ Failed to initialize Reddit client: {e}")
            return func.HttpResponse(
                json.dumps({"error": f"Reddit authentication failed: {str(e)}"}),
                status_code=500,
                mimetype="application/json"
            )

        # Process subreddits
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        total_topics = 0
        results = []

        for subreddit_name in subreddits:
            try:
                logging.info(f"🌐 Fetching hot topics from r/{subreddit_name}")
                
                # Use PRAW to get hot posts from subreddit
                subreddit = reddit.subreddit(subreddit_name)
                hot_posts = list(subreddit.hot(limit=limit))
                
                logging.info(f"📡 Successfully fetched {len(hot_posts)} posts from r/{subreddit_name}")

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

                logging.info(f"📝 Processed {len(topics)} topics from r/{subreddit_name}")

                # Create individual file for each subreddit
                blob_data = {
                    "source": source,
                    "subject": subreddit_name,
                    "fetched_at": timestamp,
                    "count": len(topics),
                    "topics": topics
                }

                # Upload to Azure Storage
                blob_name = f"{timestamp}_{source}_{subreddit_name}.json"
                logging.info(f"📤 Attempting to upload to blob: {blob_name}")

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
                    logging.info(f"✅ Successfully uploaded {len(topics)} topics from r/{subreddit_name} -> {blob_name}")
                    
                    results.append({
                        "subreddit": subreddit_name,
                        "topics_count": len(topics),
                        "blob_name": blob_name,
                        "status": "success"
                    })
                except Exception as blob_error:
                    logging.error(f"❌ Blob upload failed for r/{subreddit_name}: {blob_error}")
                    results.append({
                        "subreddit": subreddit_name,
                        "topics_count": len(topics),
                        "status": "upload_failed",
                        "error": str(blob_error)
                    })

                total_topics += len(topics)

            except Exception as e:
                logging.error(f"❌ Failed to fetch topics from r/{subreddit_name}: {e}")
                results.append({
                    "subreddit": subreddit_name,
                    "status": "fetch_failed",
                    "error": str(e)
                })

        # Prepare response
        response_data = {
            "status": "completed",
            "timestamp": timestamp,
            "source": source,
            "total_topics": total_topics,
            "total_subreddits": len(subreddits),
            "results": results
        }

        logging.info(f"🎉 Summary Wombles completed: {total_topics} total topics from {len(subreddits)} subreddits at {timestamp}")

        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"❌ Unexpected error in Summary Womble: {e}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )
