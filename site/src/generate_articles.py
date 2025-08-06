"""
Script to fetch trending topics from technology subreddits and generate markdown articles using OpenAI.
"""

import os
import requests
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_openai_key():
    # Try environment variable first (for GitHub Actions)
    if "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]
    
    # Fall back to Azure Key Vault (for production)
    keyvault_uri = os.environ["KEYVAULT_URI"]
    secret_name = os.environ["OPENAI_KEY_SECRET"]
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=keyvault_uri, credential=credential)
    secret = client.get_secret(secret_name)
    return secret.value

OPENAI_API_KEY = get_openai_key()
SUBREDDITS = ["technology", "programming", "MachineLearning", "computerscience"]
ARTICLE_COUNT = 2
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "articles"))

os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Get top posts from subreddits
def get_trending_topics():
    topics = []
    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            for post in resp.json()["data"]["children"]:
                title = post["data"]["title"]
                if not any(t["title"] == title for t in topics):
                    topics.append({"title": title, "url": post["data"]["url"]})
        if len(topics) >= ARTICLE_COUNT:
            break
    return topics[:ARTICLE_COUNT]

def generate_article(topic):
    prompt = f"Write a detailed, SEO-friendly markdown article about: {topic['title']}. Include a summary, main points, and a conclusion."
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    data = {
        "model": "gpt-4-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful tech writer."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024
    }
    resp = requests.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        return f"# {topic['title']}\n\nFailed to generate article."

def save_article(topic, content):
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = "-".join(topic["title"].lower().split())[:50]
    filename = f"{date_str}-{safe_title}.md"
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: {topic['title']}\ndate: {date_str}\n---\n\n{content}\n")

def main():
    topics = get_trending_topics()
    for topic in topics:
        content = generate_article(topic)
        save_article(topic, content)

if __name__ == "__main__":
    main()
