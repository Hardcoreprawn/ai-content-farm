import requests
import json
import os
from datetime import datetime

SUBREDDITS = [
    "technology",
    "programming",
    "MachineLearning",
    "datascience",
    "computerscience",
    "gadgets",
    "Futurology"
]
LIMIT = 10  # Number of topics per subreddit
SOURCE_NAME = "reddit"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

headers = {"User-Agent": "ai-content-farm-script/1.0"}
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

for subreddit in SUBREDDITS:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={LIMIT}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Extract more detailed topic information
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
                # First 500 chars of self-post content
                "selftext": post_data.get("selftext", "")[:500] if post_data.get("selftext") else ""
            }
            topics.append(topic)

        # Create filename: timestamp_source_subject.json
        filename = f"{timestamp}_{SOURCE_NAME}_{subreddit}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)

        # Save individual file for each subreddit
        with open(filepath, "w") as f:
            json.dump({
                "source": SOURCE_NAME,
                "subject": subreddit,
                "fetched_at": timestamp,
                "count": len(topics),
                "topics": topics
            }, f, indent=2)

        print(f"Fetched {len(topics)} topics from r/{subreddit} -> {filename}")

    except Exception as e:
        print(f"Failed to fetch topics from r/{subreddit}: {e}")

print(
    f"Completed fetching topics from {len(SUBREDDITS)} subreddits at {timestamp}")
