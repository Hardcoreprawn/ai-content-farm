# Extended Data Contracts Implementation Guide

## Overview

This guide shows how to migrate your AI Content Farm containers to use the new extensible blob format contract while maintaining full backward compatibility.

## Key Benefits

- **Provenance Tracking**: Full audit trail of data transformations, AI model usage, and costs
- **Extensibility**: Safe addition of new source types without breaking existing containers
- **Cost Management**: Track AI usage and processing costs throughout the pipeline
- **Forward Compatibility**: Add new fields safely without affecting downstream services
- **Backward Compatibility**: Existing containers continue working during migration

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Content         │    │ Extended Data    │    │ Downstream      │
│ Collector       │───▶│ Contracts        │───▶│ Services        │
│ (New Schema)    │    │ (Validator)      │    │ (Legacy Safe)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

The `ExtendedContractValidator` provides safe migration and format conversion, ensuring downstream services receive only the fields they understand.

## Migration Strategy - Phase 1: Content Collector

### 1. Update Collection Service

**File**: `containers/content-collector/service_logic.py`

```python
# Add at the top
from libs.extended_data_contracts import (
    ContentItem,
    ExtendedCollectionResult,
    CollectionMetadata,
    SourceMetadata,
    ProvenanceEntry,
    ProcessingStage,
    ExtendedContractValidator
)

class ContentCollectorService:
    """Enhanced service with extended data contracts."""
    
    async def collect_and_store_content(
        self,
        sources_data: List[Dict[str, Any]],
        deduplicate: bool = True,
        similarity_threshold: float = 0.8,
        save_to_storage: bool = True,
    ) -> Dict[str, Any]:
        """Collect content using enhanced data contracts."""
        
        start_time = time.time()
        collection_id = f"collection_{int(time.time())}"
        
        # Use enhanced collection method
        enhanced_items = await self._collect_with_enhanced_contracts(sources_data)
        
        # Create enhanced metadata
        metadata = CollectionMetadata(
            timestamp=datetime.now(timezone.utc),
            collection_id=collection_id,
            total_items=len(enhanced_items),
            sources_processed=len(sources_data),
            processing_time_ms=int((time.time() - start_time) * 1000),
            collector_version="2.0.0",  # Updated version
            collection_strategy="adaptive",
            collection_template="enhanced"
        )
        
        # Create enhanced collection result
        collection_result = ExtendedCollectionResult(
            metadata=metadata,
            items=enhanced_items,
            processing_config={
                "deduplication_enabled": deduplicate,
                "similarity_threshold": similarity_threshold
            }
        )
        
        # Calculate aggregate metrics
        collection_result.calculate_aggregate_metrics()
        
        # Save using new format
        if save_to_storage:
            storage_location = await self._save_enhanced_collection(collection_result)
        
        return {
            "collection_id": collection_id,
            "collected_items": [item.model_dump() for item in enhanced_items],
            "metadata": metadata.model_dump(),
            "storage_location": storage_location
        }
    
    async def _collect_with_enhanced_contracts(
        self, sources_data: List[Dict[str, Any]]
    ) -> List[ContentItem]:
        """Collect content and convert to enhanced format."""
        
        enhanced_items = []
        
        for source_config in sources_data:
            source_type = source_config.get("type", "")
            
            # Use existing collection logic
            collector = SourceCollectorFactory.create_collector(source_type)
            raw_items = await collector.collect_content_adaptive(source_config)
            
            # Convert to enhanced format
            for raw_item in raw_items:
                enhanced_item = self._convert_to_enhanced_item(raw_item, source_config)
                enhanced_items.append(enhanced_item)
        
        return enhanced_items
    
    def _convert_to_enhanced_item(
        self, raw_item: Dict[str, Any], source_config: Dict[str, Any]
    ) -> ContentItem:
        """Convert raw collected item to enhanced ContentItem."""
        
        source_type = source_config.get("type", "web")
        
        # Create source metadata based on type
        if source_type == "reddit":
            source_metadata = SourceMetadata(
                source_type="reddit",
                source_identifier=f"r/{raw_item.get('subreddit', 'unknown')}",
                collected_at=datetime.now(timezone.utc),
                upvotes=raw_item.get("ups"),
                comments=raw_item.get("num_comments"),
                reddit_data={
                    "subreddit": raw_item.get("subreddit"),
                    "flair": raw_item.get("link_flair_text"),
                    "author": raw_item.get("author")
                }
            )
        elif source_type == "rss":
            source_metadata = SourceMetadata(
                source_type="rss",
                source_identifier=source_config.get("feed_url", "unknown"),
                collected_at=datetime.now(timezone.utc),
                rss_data={
                    "feed_title": raw_item.get("feed_title"),
                    "category": raw_item.get("category"),
                    "published": raw_item.get("published")
                }
            )
        else:
            # Generic web source
            source_metadata = SourceMetadata(
                source_type=source_type,
                source_identifier=raw_item.get("url", "unknown"),
                collected_at=datetime.now(timezone.utc),
                custom_fields=raw_item.get("source_specific_data", {})
            )
        
        # Create enhanced content item
        content_item = ContentItem(
            id=raw_item.get("id", str(uuid4())),
            title=raw_item.get("title", "Untitled"),
            url=raw_item.get("url"),
            content=raw_item.get("content") or raw_item.get("selftext"),
            summary=raw_item.get("summary"),
            source=source_metadata
        )
        
        # Add collection provenance
        collection_provenance = ProvenanceEntry(
            stage=ProcessingStage.COLLECTION,
            service_name="content-collector",
            service_version="2.0.0",
            operation=f"{source_type}_collection",
            processing_time_ms=raw_item.get("collection_time_ms", 0),
            parameters={
                "collection_method": "adaptive",
                "source_config": source_config
            }
        )
        content_item.add_provenance(collection_provenance)
        
        return content_item
```

### 2. Update Storage Method

```python
async def _save_enhanced_collection(
    self, collection_result: ExtendedCollectionResult
) -> str:
    """Save collection using enhanced format with backward compatibility."""
    
    # Generate storage path
    timestamp = datetime.now(timezone.utc)
    container_name = BlobContainers.COLLECTED_CONTENT
    blob_name = f"collections/{timestamp.strftime('%Y/%m/%d')}/{collection_result.metadata.collection_id}.json"
    
    # Save enhanced format
    enhanced_json = collection_result.model_dump_json(indent=2)
    await self.storage.upload_text(
        container=container_name,
        blob_name=blob_name,
        text=enhanced_json,
    )
    
    # OPTIONAL: Also save legacy format for immediate compatibility
    legacy_format = ExtendedContractValidator.create_safe_collection_for_downstream(collection_result)
    legacy_blob_name = f"collections/legacy/{timestamp.strftime('%Y/%m/%d')}/{collection_result.metadata.collection_id}_legacy.json"
    
    await self.storage.upload_json(
        container=container_name,
        blob_name=legacy_blob_name,
        data=legacy_format
    )
    
    return f"{container_name}/{blob_name}"
```

## Migration Strategy - Phase 2: Content Processor

### 1. Update Processing Service

**File**: `containers/content-processor/endpoints/processing.py`

```python
# Add enhanced contract support
from libs.extended_data_contracts import (
    ExtendedContractValidator,
    ContentItem,
    ProvenanceEntry,
    ProcessingStage
)

@router.post("/wake-up")
async def wake_up_processor(request: WakeUpRequest, metadata: Dict[str, Any] = Depends(service_metadata)):
    """Enhanced wake-up processor with contract validation."""
    
    try:
        blob_client = SimplifiedBlobClient()
        
        # Get latest collection
        blobs = await blob_client.list_blobs("collected-content", prefix="collections/")
        if not blobs:
            return StandardResponse(
                status="success",
                data={"topics_processed": 0},
                message="No collections found"
            )
        
        latest_blob = sorted(blobs, key=lambda x: x["name"])[-1]
        collection_data = await blob_client.download_json("collected-content", latest_blob["name"])
        
        # Validate and migrate collection data
        try:
            validated_collection = ExtendedContractValidator.validate_collection_data(collection_data)
            logger.info(f"Using enhanced format with {len(validated_collection.items)} items")
        except Exception as e:
            logger.warning(f"Failed to parse as enhanced format, using legacy: {e}")
            # Fall back to legacy processing
            return await legacy_wake_up_processing(collection_data, request, metadata)
        
        # Process using enhanced format
        processed_items = []
        for item in validated_collection.items[:request.batch_size]:
            
            # Enhanced processing with provenance
            processed_item = await process_enhanced_item(item)
            processed_items.append(processed_item)
        
        return StandardResponse(
            status="success",
            data={
                "topics_processed": len(processed_items),
                "collection_processed": latest_blob["name"],
                "total_cost_usd": sum(item.get_total_cost() for item in processed_items),
                "average_quality": sum(item.quality_score or 0 for item in processed_items) / len(processed_items)
            },
            message=f"Enhanced processing complete: {len(processed_items)} items"
        )
        
    except Exception as e:
        logger.error(f"Enhanced processing failed: {e}")
        return StandardResponse(status="error", message="Processing failed", errors=[str(e)])

async def process_enhanced_item(item: ContentItem) -> ContentItem:
    """Process item with enhanced provenance tracking."""
    
    start_time = time.time()
    
    # Simulate AI enhancement
    enhanced_content = f"[AI Enhanced] {item.content or ''}"
    item.content = enhanced_content
    item.quality_score = 0.85  # Simulated
    
    # Add processing provenance
    processing_provenance = ProvenanceEntry(
        stage=ProcessingStage.PROCESSING,
        service_name="content-processor",
        service_version="2.1.0",
        operation="ai_enhancement",
        processing_time_ms=int((time.time() - start_time) * 1000),
        ai_model="gpt-4o-mini",
        prompt_tokens=200,
        completion_tokens=300,
        total_tokens=500,
        cost_usd=0.0025,
        quality_score=0.85,
        parameters={"enhancement_type": "standard"}
    )
    
    item.add_provenance(processing_provenance)
    return item
```

## Migration Strategy - Phase 3: Gradual Rollout

### 1. Environment Variables for Control

```bash
# Control enhanced contracts usage
ENHANCED_CONTRACTS_ENABLED=true
LEGACY_COMPATIBILITY_MODE=true
SAVE_BOTH_FORMATS=true  # During transition
```

### 2. Feature Flags in Code

```python
class ContentCollectorService:
    def __init__(self):
        self.enhanced_contracts_enabled = os.getenv("ENHANCED_CONTRACTS_ENABLED", "false").lower() == "true"
        self.legacy_compatibility = os.getenv("LEGACY_COMPATIBILITY_MODE", "true").lower() == "true"
        self.save_both_formats = os.getenv("SAVE_BOTH_FORMATS", "false").lower() == "true"
    
    async def collect_and_store_content(self, ...):
        if self.enhanced_contracts_enabled:
            return await self._collect_with_enhanced_contracts(...)
        else:
            return await self._collect_with_legacy_contracts(...)
```

### 3. Monitoring and Validation

```python
# Add to diagnostics endpoints
@router.get("/contracts/status")
async def get_contracts_status():
    """Get current data contracts status."""
    
    return {
        "enhanced_contracts_enabled": os.getenv("ENHANCED_CONTRACTS_ENABLED", "false"),
        "legacy_compatibility": os.getenv("LEGACY_COMPATIBILITY_MODE", "true"),
        "schema_versions_supported": ["2.0", "3.0"],
        "migration_phase": "rollout"
    }

@router.post("/contracts/validate")
async def validate_collection_format(blob_path: str):
    """Validate a collection against both formats."""
    
    try:
        blob_client = SimplifiedBlobClient()
        data = await blob_client.download_json("collected-content", blob_path)
        
        # Test enhanced format
        try:
            enhanced = ExtendedContractValidator.validate_collection_data(data)
            enhanced_valid = True
        except Exception as e:
            enhanced_valid = False
            enhanced_error = str(e)
        
        # Test legacy compatibility
        try:
            legacy = ExtendedContractValidator.create_safe_collection_for_downstream(enhanced)
            legacy_valid = True
        except Exception as e:
            legacy_valid = False
            legacy_error = str(e)
        
        return {
            "enhanced_format_valid": enhanced_valid,
            "legacy_compatible": legacy_valid,
            "schema_version": data.get("schema_version", "unknown")
        }
        
    except Exception as e:
        return {"error": str(e)}
```

## Testing Strategy

### 1. Unit Tests

```python
# Test enhanced format creation
def test_enhanced_collection_creation():
    # Test creating collections with new format
    pass

# Test backward compatibility
def test_legacy_service_compatibility():
    # Test that legacy services can consume enhanced format
    pass

# Test migration
def test_format_migration():
    # Test migrating old format to new
    pass
```

### 2. Integration Tests

```python
# Test end-to-end pipeline
async def test_enhanced_pipeline_flow():
    # Collection → Processing → Site Generation with enhanced format
    pass
```

### 3. A/B Testing

Run both formats in parallel and compare:
- Processing success rates
- Performance metrics
- Cost tracking accuracy
- Downstream service compatibility

## Deployment Plan

1. **Phase 1**: Deploy enhanced contracts library
2. **Phase 2**: Update content-collector with feature flag (disabled)
3. **Phase 3**: Enable enhanced contracts for content-collector (save both formats)
4. **Phase 4**: Update content-processor to consume enhanced format
5. **Phase 5**: Update site-generator to use enhanced format
6. **Phase 6**: Stop saving legacy format
7. **Phase 7**: Remove legacy compatibility code

## Rollback Strategy

If issues arise:

1. **Immediate**: Set `ENHANCED_CONTRACTS_ENABLED=false`
2. **Short-term**: Use legacy blob paths: `collections/legacy/...`
3. **Long-term**: Revert container versions to previous stable

## Monitoring

Track these metrics during migration:

- **Format Distribution**: % enhanced vs legacy
- **Processing Success Rate**: Enhanced vs legacy format
- **Performance**: Processing time comparison
- **Costs**: AI usage and cost tracking accuracy
- **Errors**: Validation failures and migration issues

## Benefits Realized

After full migration:

1. **Cost Transparency**: Track exact AI costs per item/collection
2. **Quality Assurance**: Monitor quality scores throughout pipeline
3. **Audit Trail**: Complete provenance from collection to publication
4. **Extensibility**: Add new sources without breaking existing services
5. **Performance Optimization**: Identify bottlenecks with detailed timing
6. **Future-Proofing**: Schema designed for evolution

## Example Usage

```python
# Create enhanced collection
collection = ExtendedCollectionResult(...)
collection.calculate_aggregate_metrics()

# Save enhanced format
await storage.upload_json("collected-content", "collection.json", collection.model_dump())

# Legacy service consumption
safe_format = ExtendedContractValidator.create_safe_collection_for_downstream(collection)
# Legacy services process safe_format normally

# Cost analysis
total_cost = collection.metadata.total_cost_usd
cost_per_item = total_cost / collection.metadata.total_items
```

This migration maintains full backward compatibility while enabling powerful new capabilities for cost tracking, provenance, and extensibility.