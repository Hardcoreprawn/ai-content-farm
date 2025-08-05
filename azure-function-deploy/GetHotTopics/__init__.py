import logging
import azure.functions as func
import requests
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential


def main(mytimer: func.TimerRequest) -> None:
    logging.info('🚀 Python timer trigger function started.')

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

    headers = {"User-Agent": "ai-content-farm-azure-function/1.0"}
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    total_topics = 0

    for subreddit in SUBREDDITS:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={LIMIT}"
        try:
            logging.info(f"🌐 Fetching topics from r/{subreddit}")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            logging.info(
                f"📡 Successfully fetched data from r/{subreddit}, got {len(data.get('data', {}).get('children', []))} posts")

            # Extract detailed topic information
            topics = []
            for post in data["data"]["children"]:
                post_data = post["data"]

                # Get both external URL and Reddit discussion URL
                external_url = post_data.get("url", "")
                reddit_url = f"https://www.reddit.com{post_data.get('permalink', '')}"
                post_id = post_data.get("id", "")

                topic = {
                    "title": post_data["title"],
                    "external_url": external_url,
                    "reddit_url": reddit_url,
                    "reddit_id": post_id,
                    "score": post_data.get("score", 0),
                    "created_utc": post_data.get("created_utc", 0),
                    "num_comments": post_data.get("num_comments", 0),
                    "author": post_data.get("author", ""),
                    "subreddit": subreddit,
                    "fetched_at": timestamp,
                    "selftext": post_data.get("selftext", "")[:500] if post_data.get("selftext") else ""
                }
                topics.append(topic)

            logging.info(
                f"📝 Processed {len(topics)} topics from r/{subreddit}")

            # Create individual file for each subreddit
            blob_data = {
                "source": SOURCE_NAME,
                "subject": subreddit,
                "fetched_at": timestamp,
                "count": len(topics),
                "topics": topics
            }

            # Upload to Azure Storage
            blob_name = f"{timestamp}_{SOURCE_NAME}_{subreddit}.json"
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
                    f"✅ Successfully uploaded {len(topics)} topics from r/{subreddit} -> {blob_name}")
            except Exception as blob_error:
                logging.error(
                    f"❌ Blob upload failed for r/{subreddit}: {blob_error}")
                raise

            total_topics += len(topics)
            logging.info(
                f"✅ Uploaded {len(topics)} topics from r/{subreddit} -> {blob_name}")

        except Exception as e:
            logging.error(f"❌ Failed to fetch topics from r/{subreddit}: {e}")

    logging.info(
        f"🎉 Completed womble run: {total_topics} total topics from {len(SUBREDDITS)} subreddits at {timestamp}")

    if mytimer.past_due:
        logging.info('⚠️ The timer is past due!')

    logging.info('✅ Function execution completed successfully.')

    if mytimer.past_due:
        logging.info('The timer is past due!')
