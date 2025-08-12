#!/usr/bin/env python3
"""
Show status of womble runs and topic files.
"""
import os
import glob
import json
from datetime import datetime


def show_sample_sources(filepath):
    """Show sample source URLs from a topic file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        topics = data.get('topics', [])
        if topics:
            print(
                f"\n🔗 Sample sources from {data.get('source', 'unknown')}:{data.get('subject', 'unknown')}:")
            for i, topic in enumerate(topics[:3]):  # Show first 3
                title = topic.get('title', 'No title')[
                    :60] + '...' if len(topic.get('title', '')) > 60 else topic.get('title', 'No title')
                external_url = topic.get(
                    'external_url', topic.get('url', 'No URL'))
                reddit_url = topic.get('reddit_url', 'No Reddit URL')
                print(f"   {i+1}. {title}")
                print(f"      🌐 External: {external_url}")
                print(f"      💬 Reddit: {reddit_url}")
    except Exception as e:
        print(f"\n❌ Error reading sample file: {e}")


def show_status():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")

    print("=== WOMBLE STATUS ===")
    print(f"Output directory: {output_dir}")

    # Find all topic files (expand pattern to include all sources)
    pattern = os.path.join(output_dir, "*_*_*.json")
    files = sorted(glob.glob(pattern), reverse=True)

    if not files:
        print("No topic files found!")
        return

    # Group by timestamp
    timestamps = {}
    for filepath in files:
        filename = os.path.basename(filepath)
        parts = filename.split("_")
        if len(parts) >= 4:
            timestamp = f"{parts[0]}_{parts[1]}"
            if timestamp not in timestamps:
                timestamps[timestamp] = []
            timestamps[timestamp].append(filename)

    print(f"\nFound {len(files)} topic files from {len(timestamps)} runs:")

    # Show last 3 runs
    for timestamp in sorted(timestamps.keys(), reverse=True)[:3]:
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        print(f"\n📅 {dt.strftime('%Y-%m-%d %H:%M:%S')} ({timestamp})")
        for filename in sorted(timestamps[timestamp]):
            filepath = os.path.join(output_dir, filename)
            size = os.path.getsize(filepath)
            parts = filename.split("_")
            source = parts[2] if len(parts) > 2 else "unknown"
            subject = parts[3].replace(".json", "") if len(
                parts) > 3 else "unknown"
            print(f"   📊 {source}:{subject:<14} ({size:,} bytes)")

    # Show sample source URLs from latest run
    if timestamps:
        latest_timestamp = sorted(timestamps.keys(), reverse=True)[0]
        latest_files = timestamps[latest_timestamp]
        if latest_files:
            sample_file = os.path.join(output_dir, latest_files[0])
            show_sample_sources(sample_file)


if __name__ == "__main__":
    show_status()
