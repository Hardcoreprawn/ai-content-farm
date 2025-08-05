import logging
import azure.functions as func
import praw
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def main(mytimer: func.TimerRequest) -> None:
    logging.info('🚀 Summary Wombles timer trigger function started.')

    # Configuration
    SUBREDDITS = [
        "technology",
        "programming",
        "MachineLearning",
        "datascience",
        "computerscience",
        "gadgets",
        "Futurology"
    ]
    LIMIT = 10
    SOURCE_NAME = "reddit"

    # Azure Storage configuration
    storage_account_name = os.environ.get("OUTPUT_STORAGE_ACCOUNT")
    container_name = os.environ.get("OUTPUT_CONTAINER", "hot-topics")

    logging.info(f"🔧 Storage account name: {storage_account_name}")
    logging.info(f"🔧 Container name: {container_name}")

    if not storage_account_name:
        logging.error(
            "❌ OUTPUT_STORAGE_ACCOUNT not found in environment variables")
        return

    try:
        # Use managed identity to authenticate to storage
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            account_url=f"https://{storage_account_name}.blob.core.windows.net",
            credential=credential
        )
        logging.info(
            "✅ Blob service client created successfully with managed identity")
    except Exception as e:
        logging.error(f"❌ Failed to create blob service client: {e}")
        return

    # Get Reddit API credentials from Key Vault
    try:
        # Key Vault URL - using the same Key Vault we configured
        key_vault_url = f"https://hottopicskvib91ea.vault.azure.net"
        secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
        
        reddit_client_id = secret_client.get_secret("reddit-client-id").value
        reddit_client_secret = secret_client.get_secret("reddit-client-secret").value
        
        logging.info("✅ Successfully retrieved Reddit API credentials from Key Vault")
    except Exception as e:
        logging.error(f"❌ Failed to retrieve Reddit credentials from Key Vault: {e}")
        return

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
        return

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    total_topics = 0

    for subreddit_name in SUBREDDITS:
        try:
            logging.info(f"🌐 Fetching hot topics from r/{subreddit_name}")
            
            # Use PRAW to get hot posts from subreddit
            subreddit = reddit.subreddit(subreddit_name)
            hot_posts = list(subreddit.hot(limit=LIMIT))
            
            logging.info(
                f"📡 Successfully fetched {len(hot_posts)} posts from r/{subreddit_name}")

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

            logging.info(
                f"📝 Processed {len(topics)} topics from r/{subreddit_name}")

            # Create individual file for each subreddit
            blob_data = {
                "source": SOURCE_NAME,
                "subject": subreddit_name,
                "fetched_at": timestamp,
                "count": len(topics),
                "topics": topics
            }

            # Upload to Azure Storage
            blob_name = f"{timestamp}_{SOURCE_NAME}_{subreddit_name}.json"
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
                logging.info(
                    f"✅ Successfully uploaded {len(topics)} topics from r/{subreddit_name} -> {blob_name}")
            except Exception as blob_error:
                logging.error(
                    f"❌ Blob upload failed for r/{subreddit_name}: {blob_error}")
                raise

            total_topics += len(topics)

        except Exception as e:
            logging.error(f"❌ Failed to fetch topics from r/{subreddit_name}: {e}")

    logging.info(
        f"🎉 Summary Wombles completed: {total_topics} total topics from {len(SUBREDDITS)} subreddits at {timestamp}")

    if mytimer.past_due:
        logging.info('⚠️ The timer is past due!')

    logging.info('✅ Summary Wombles function execution completed successfully.')
