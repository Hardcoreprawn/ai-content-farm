#!/usr/bin/env python3
"""
Test the event-driven blob watching functionality
"""

import os
import json
import asyncio
import sys
from datetime import datetime

# Add the containers directory to the path
sys.path.append("/workspaces/ai-content-farm/containers/content-generator")
sys.path.append("/workspaces/ai-content-farm")


async def test_event_driven_generation():
    """Test event-driven content generation by uploading ranked content"""

    # Set up environment variables for testing
    os.environ["AZURE_STORAGE_ACCOUNT_NAME"] = "aicontentfarm76ko2h"
    os.environ["ENVIRONMENT"] = "development"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://uksouth.api.cognitive.microsoft.com/"
    os.environ["AZURE_OPENAI_API_KEY"] = os.getenv(
        "AZURE_OPENAI_API_KEY", "mock-test-key-for-development"
    )
    os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "gpt-4o-mini"

    print("🎯 Testing Event-Driven Content Generation")
    print("=" * 50)

    try:
        from libs.blob_storage import get_blob_client

        # Get blob client
        blob_client = get_blob_client()
        print("✅ Connected to blob storage")

        # Create rich test content for generation
        test_ranked_content = {
            "topics": [
                {
                    "topic": "Advanced Machine Learning in Healthcare Diagnostics",
                    "sources": [
                        {
                            "name": "Medical AI Research Institute",
                            "url": "https://example.com/medical-ai-diagnostics",
                            "title": "AI Achieves 95% Accuracy in Early Cancer Detection",
                            "summary": "Revolutionary AI system demonstrates unprecedented accuracy in medical imaging analysis",
                            "content": "A groundbreaking artificial intelligence system has achieved 95% accuracy in early cancer detection through advanced medical imaging analysis. The AI model, trained on over 1 million medical scans, can identify subtle patterns invisible to the human eye. Early trials show the system can detect cancers 18 months earlier than traditional methods, potentially saving thousands of lives annually. The technology combines deep learning with specialized computer vision algorithms optimized for medical imagery. Radiologists working with the AI system report improved diagnostic confidence and reduced examination times. The system has been tested across multiple cancer types including lung, breast, and prostate cancers with consistently high performance metrics.",
                            "metadata": {
                                "source_type": "research",
                                "credibility_score": 9.5,
                                "publication_date": "2025-08-19",
                            },
                        },
                        {
                            "name": "Healthcare Technology Review",
                            "url": "https://example.com/ai-healthcare-implementation",
                            "title": "Hospitals Begin Wide-Scale AI Diagnostic Implementation",
                            "summary": "Major medical centers adopting AI-powered diagnostic tools",
                            "content": "Leading hospitals across North America and Europe are implementing AI-powered diagnostic tools at an unprecedented scale. Massachusetts General Hospital reports 40% faster diagnosis times and 25% improvement in early detection rates since deploying the AI system six months ago. The technology integrates seamlessly with existing PACS (Picture Archiving and Communication Systems) and provides real-time analysis during routine screenings. Training programs for radiologists and technicians have shown high adoption rates, with 89% of medical staff rating the AI assistance as 'extremely helpful' in their daily workflow. Cost analysis indicates a 30% reduction in diagnostic errors and associated litigation costs.",
                            "metadata": {
                                "source_type": "industry_analysis",
                                "credibility_score": 8.8,
                                "publication_date": "2025-08-18",
                            },
                        },
                        {
                            "name": "Journal of Medical Innovation",
                            "url": "https://example.com/ai-diagnostic-ethics",
                            "title": "Ethical Considerations in AI-Assisted Medical Diagnosis",
                            "summary": "Addressing privacy, bias, and accountability in medical AI systems",
                            "content": "The rapid adoption of AI in medical diagnostics raises important ethical questions about patient privacy, algorithmic bias, and professional accountability. Medical ethicists emphasize the need for transparent AI systems that can explain their diagnostic reasoning. Recent studies highlight potential bias in AI models trained on demographically homogeneous datasets, leading to disparate outcomes for minority populations. Regulatory frameworks are evolving to address these challenges, with new guidelines requiring diverse training data and regular bias audits. The medical community is developing best practices for AI-human collaboration that maintain physician oversight while leveraging AI capabilities. Patient consent protocols are being updated to address AI-assisted diagnosis and data usage.",
                            "metadata": {
                                "source_type": "academic",
                                "credibility_score": 9.2,
                                "publication_date": "2025-08-17",
                            },
                        },
                    ],
                    "rank": 1,
                    "ai_score": 94.7,
                    "sentiment": "positive",
                    "tags": [
                        "artificial intelligence",
                        "healthcare",
                        "medical diagnosis",
                        "machine learning",
                        "cancer detection",
                    ],
                    "metadata": {
                        "category": "healthcare_technology",
                        "keywords": [
                            "AI",
                            "medical imaging",
                            "cancer detection",
                            "healthcare",
                            "machine learning",
                        ],
                        "ranking_timestamp": "2025-08-19T20:45:00Z",
                        "trending_score": 88.5,
                        "engagement_score": 91.2,
                        "source_quality": 9.2,
                    },
                }
            ],
            "metadata": {
                "batch_id": "ranker_20250819_204500_event_test",
                "ranking_timestamp": "2025-08-19T20:45:00Z",
                "total_topics_processed": 247,
                "selected_topics": 1,
                "ranking_criteria": {
                    "engagement_weight": 0.4,
                    "recency_weight": 0.35,
                    "quality_weight": 0.25,
                },
                "source": "content_ranker",
                "version": "1.0.0",
            },
        }

        # Upload to ranked-content container
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"ranker_{timestamp}_event_test.json"

        try:
            blob_url = blob_client.upload_json(
                container_name="ranked-content",
                blob_name=blob_name,
                data=test_ranked_content,
                metadata={
                    "test_type": "event_driven_generation",
                    "topics_count": "1",
                    "test_timestamp": datetime.utcnow().isoformat(),
                },
            )
            print(f"✅ Uploaded test ranked content: {blob_name}")
            print(f"   Blob URL: {blob_url}")
            print(f"   Topics: {len(test_ranked_content['topics'])}")

            # The content generator should detect this blob and generate content automatically
            print(
                "\n⏳ Content generator should automatically detect and process this blob..."
            )
            print("   Check the 'generated-content' container for results")
            print("   (This may take 30-60 seconds as the watcher checks every 30s)")

            return True

        except Exception as e:
            print(f"❌ Failed to upload test content: {e}")
            print("   This might be due to blob storage permissions")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_event_driven_generation())
    sys.exit(0 if result else 1)
