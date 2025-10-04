# Pipeline Deduplication & Processing State Management

## Overview

The pipeline currently has **LIMITED** tracking of what's been processed. Here's how each stage handles duplicates and processing state:

---

## 🔵 Stage 1: Content Collection (content-collector)

### Current Behavior
**Within-batch deduplication only** - No cross-batch tracking

### How It Works
```python
# content_processing.py - deduplicate_content()
seen_hashes = set()
seen_titles = set()

for item in items:
    content_hash = hashlib.md5(f"{title}:{content}".encode()).hexdigest()
    
    if content_hash in seen_hashes or title_lower in seen_titles:
        continue  # Skip duplicate
    
    deduplicated_items.append(item)
```

### What This Means
- ✅ **Duplicates within a single collection run are removed**
- ❌ **No memory of previously collected content**
- ❌ **If you run collection twice, you'll get duplicates across runs**

### Storage Pattern
- Saves to: `collected-content/` container
- Filename: `collection-{timestamp}.json` (new file each time)
- Format: `CollectionResult` with multiple items

---

## 🟢 Stage 2: Content Processing (content-processor)

### Current Behavior
**No duplicate checking** - Processes everything it finds

### How It Works
```python
# processor.py - wake_up()
topics = await self.topic_discovery.discover_unprocessed_topics(
    batch_size=batch_size,
    priority_threshold=priority_threshold
)

for topic_metadata in topics:
    # Process each topic
    result = await self._process_single_topic(topic_metadata)
    
    # Save to processed-content container
    await self.storage.save_processed_article(article_result)
```

### What This Means
- ❌ **No check if topic was already processed**
- ❌ **Will reprocess the same topic if it appears in multiple collection files**
- ✅ **Each processed article saves to its own blob file**

### Storage Pattern
- Reads from: `collected-content/` container
- Saves to: `processed-content/` container  
- Filename: `article-{topic_id}-{timestamp}.json` (unique per processing)
- **Note**: Same topic processed twice = two different files

---

## 🟡 Stage 3: Markdown Generation (site-generator)

### Current Behavior
**Basic file-exists checking** - Skips if file already exists (unless forced)

### How It Works
```python
# content_utility_functions.py - generate_article_markdown()
if not force_regenerate:
    existing_blobs = await blob_client.list_blobs(container=container_name)
    if any(blob["name"] == markdown_filename for blob in existing_blobs):
        logger.debug(f"Skipping existing file: {markdown_filename}")
        return markdown_filename  # Skip - already exists
```

### What This Means
- ✅ **Will NOT regenerate existing markdown files** (by default)
- ⚠️ **Filename based on article title** - collisions possible
- ❌ **Doesn't check if source article was updated**

### Storage Pattern
- Reads from: `processed-content/` container
- Saves to: `markdown-content/` container
- Filename: `{safe-title}.md` (based on article title)
- **Problem**: Two articles with same title → filename collision

---

## 🔴 Stage 4: HTML Generation (site-generator)

### Current Behavior
**Always regenerates everything** - No caching or skipping

### How It Works
```python
# content_utility_functions.py - create_complete_site()
processed_articles = prepare_articles_for_display(articles)

for article in processed_articles:
    # ALWAYS generate HTML (overwrite=True)
    html_content = generate_article_page(article=article, config=config)
    await blob_client.upload_text(
        container=config["STATIC_SITES_CONTAINER"],
        blob_name=filename,
        text=html_content,
        overwrite=True  # Always overwrites
    )
```

### What This Means
- ❌ **Regenerates ALL HTML on every run**
- ✅ **Always has fresh content from markdown**
- ⚠️ **Index page is always regenerated** (which we just fixed to deduplicate!)

### Storage Pattern
- Reads from: `markdown-content/` container
- Saves to: `$web/` container (public static site)
- Filename: `articles/{article_id}-{safe_title}.html`
- **Always overwrites**: Every site generation rewrites all files

---

## 📊 Summary Table

| Stage | Deduplication | Skips Existing? | Cross-Run Memory? |
|-------|---------------|-----------------|-------------------|
| **Collection** | Within-batch only | No | ❌ No |
| **Processing** | None | No | ❌ No |
| **Markdown Gen** | By filename | Yes (default) | ⚠️ Limited |
| **HTML Gen** | By article ID | No (always regenerates) | ❌ No |

---

## 🚨 Current Problems

### 1. **Collection Duplicates Across Runs**
If you run the collector twice:
- First run: Collects 10 articles → `collection-20251004-120000.json`
- Second run: Collects same 10 articles → `collection-20251004-130000.json`
- **Result**: 20 articles in storage (10 duplicates)

### 2. **Processing Will Process Duplicates**
The processor reads ALL files in `collected-content/`:
- Finds both collection files from above
- Processes all 20 articles (including duplicates)
- Creates 20 processed article files

### 3. **Markdown May Skip or Collide**
- Articles with same title → same filename → one overwrites the other
- Or skips if file exists (but doesn't check if content changed)

### 4. **HTML Always Regenerates**
- Even if nothing changed, entire site is rebuilt
- Good for consistency, but wasteful

---

## 🎯 Your Deduplication Fix (index.html)

Your recent fix handles **display-time deduplication**:

```python
# article_processing.py - deduplicate_articles()
seen_ids = {}
for article in articles:
    article_id = article.get('id') or article.get('topic_id') or article.get('slug', '')
    
    if article_id not in seen_ids:
        seen_ids[article_id] = article
    else:
        # Keep newer version
        if current_date > existing_date:
            seen_ids[article_id] = article
```

**This fixes the symptom (duplicate display) but not the root cause (duplicate processing).**

---

## 💡 Recommended Improvements

### Short-term (Quick Wins)

1. **Content Collector: Add collection history**
   ```python
   # Before collecting, check previous collection files
   previous_items = await load_recent_collections(hours=24)
   new_items = [item for item in items if item['id'] not in previous_items]
   ```

2. **Content Processor: Track processed topics**
   ```python
   # Check if topic already processed
   processed_topics = await list_processed_articles()
   unprocessed = [t for t in topics if t.topic_id not in processed_topics]
   ```

3. **Markdown Generator: Check content hash**
   ```python
   # Don't skip just by filename - check if content changed
   if file_exists and content_hash_matches:
       skip
   ```

### Long-term (Production Ready)

1. **Implement metadata tracking database**
   - Azure Table Storage or Cosmos DB
   - Track: article_id, collection_time, processing_time, generation_time
   - Fast lookups: "Has this been processed before?"

2. **Add content fingerprinting**
   - Hash article content
   - Detect if article content changed
   - Only regenerate if content differs

3. **Implement incremental builds**
   - Only regenerate changed articles
   - Update index only if articles changed
   - Cache static assets

---

## 🔧 Current Workaround

For now, the pipeline relies on:
1. **Time-based collection** - Only collect recent items (reduces duplicates)
2. **Batch limits** - Process limited number at a time
3. **Display deduplication** - Your new fix handles display layer
4. **Manual cleanup** - Periodically clean old collection files

---

## 📝 Questions Answered

> "How does the pipeline know collected content has been processed, and not to process it again?"

**Answer**: It doesn't. The processor will process everything in the `collected-content` container, including duplicates.

> "And the same thing about generating markdown or html?"

**Answer**:
- **Markdown**: Checks if filename exists, skips if found (unless `force_regenerate=True`)
- **HTML**: Always regenerates everything (no skipping)

---

## 🎓 Design Philosophy

The current design follows a **"stateless, idempotent processing"** pattern:
- Each stage can be run independently
- Re-running is safe (mostly - just creates duplicates)
- No complex state management
- Simple to debug and reason about

**Trade-off**: Simplicity vs. efficiency (duplicates are tolerated for simplicity)

Your deduplication fix is a great **pragmatic middle ground** - keeps the simple pipeline but prevents duplicate display!
