#!/usr/bin/env python3
"""
Mock OpenAI Service for Testing and Development

Provides a realistic mock of OpenAI functionality for testing and development
environments where actual OpenAI credentials are not available.

This maintains the same interface as the real service but uses simulated responses.
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, Optional, Tuple

from services.openai_service import ModelTier, ProcessingType

logger = logging.getLogger(__name__)


class MockContentProcessor:
    """
    Mock content processor that simulates OpenAI behavior for testing.

    Features the same interface as the real ContentProcessor but returns
    simulated responses that look realistic for testing purposes.
    """

    def __init__(self):
        self.processing_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_cost": 0.0,
            "region_usage": {"uk_south": 0, "west_europe": 0, "primary": 0},
        }
        self.model_configs = {
            "gpt-3.5-turbo": {
                "tier": ModelTier.STANDARD,
                "cost_per_1k_tokens": 0.0015,
                "max_tokens": 4096,
                "suitable_for": [
                    ProcessingType.GENERAL,
                    ProcessingType.CONTENT_ANALYSIS,
                ],
                "region": "uk_south",
            },
            "gpt-4": {
                "tier": ModelTier.ADVANCED,
                "cost_per_1k_tokens": 0.03,
                "max_tokens": 8192,
                "suitable_for": [
                    ProcessingType.ARTICLE_GENERATION,
                    ProcessingType.QUALITY_ASSESSMENT,
                ],
                "region": "west_europe",
            },
            "gpt-4-turbo": {
                "tier": ModelTier.PREMIUM,
                "cost_per_1k_tokens": 0.01,
                "max_tokens": 128000,
                "suitable_for": [
                    ProcessingType.TOPIC_EXPANSION,
                    ProcessingType.ARTICLE_GENERATION,
                ],
                "region": "west_europe",
            },
        }

    def _generate_mock_content(
        self, content: str, processing_type: ProcessingType, options: Dict[str, Any]
    ) -> str:
        """Generate realistic mock processed content."""

        content_length = len(content)
        voice = options.get("voice", "professional")
        target_audience = options.get("target_audience", "general")

        if processing_type == ProcessingType.ARTICLE_GENERATION:
            return f"""# {content.strip()}

## Introduction

This comprehensive article explores the topic of "{content.strip()}" with a {voice} approach tailored for {target_audience} audiences.

## Key Points

1. **Foundation**: Understanding the core concepts and principles
2. **Implementation**: Practical approaches and methodologies
3. **Benefits**: Advantages and positive outcomes
4. **Challenges**: Potential obstacles and solutions
5. **Future Outlook**: Trends and developments

## Detailed Analysis

[Mock content generated for testing - would be full article content in production]

The topic demonstrates significant relevance across multiple domains, offering both immediate practical applications and long-term strategic value.

## Conclusion

This analysis of "{content.strip()}" reveals important insights that can inform decision-making and strategic planning for {target_audience} stakeholders.

*Generated in {voice} voice for {target_audience} audience using mock AI processing.*
"""
        elif processing_type == ProcessingType.CONTENT_ANALYSIS:
            return f"""# Content Analysis Report

## Content Overview
- **Original Length**: {content_length} characters
- **Estimated Reading Time**: {content_length // 200} minutes
- **Content Type**: General text content

## Quality Assessment
- **Clarity Score**: 8.5/10
- **Engagement Score**: 7.8/10
- **Structure Score**: 8.2/10
- **Overall Quality**: 8.2/10

## Key Findings
- Well-structured content with clear messaging
- Appropriate for {target_audience} audience
- Maintains {voice} tone throughout
- Opportunities for enhancement in specific areas

## Recommendations
1. Consider expanding certain sections for better depth
2. Add more specific examples to illustrate key points
3. Enhance transitions between sections
4. Include call-to-action elements where appropriate

## Content Metrics
- **Word Count**: ~{content_length // 5} words
- **Readability**: Grade 8-10 level
- **Sentiment**: Neutral to positive
- **Technical Depth**: Moderate

*Analysis generated using mock AI content analysis for testing purposes.*
"""
        elif processing_type == ProcessingType.QUALITY_ASSESSMENT:
            quality_score = random.uniform(0.7, 0.95)
            return f"""# Quality Assessment Score: {quality_score:.2f}/1.00

## Assessment Summary
The content demonstrates strong overall quality with a score of {quality_score:.2f} out of 1.00.

## Detailed Scoring
- **Content Quality**: {quality_score + 0.02:.2f}/1.00
- **Structure & Organization**: {quality_score - 0.03:.2f}/1.00
- **Clarity & Readability**: {quality_score + 0.01:.2f}/1.00
- **Audience Alignment**: {quality_score:.2f}/1.00
- **Voice Consistency**: {quality_score + 0.04:.2f}/1.00

## Strengths
- Clear and engaging presentation
- Appropriate {voice} voice for {target_audience} audience
- Well-organized structure
- Good use of examples and supporting details

## Areas for Improvement
- Could benefit from more specific examples
- Consider enhancing call-to-action elements
- Opportunity to add more interactive elements

## Recommendation
**APPROVED** - Content meets quality standards for publication with minor enhancements suggested.

*Quality assessment generated using mock AI evaluation for testing purposes.*
"""
        elif processing_type == ProcessingType.TOPIC_EXPANSION:
            return f"""# Comprehensive Topic Expansion: {content.strip()}

## Executive Summary
This expanded exploration of "{content.strip()}" provides comprehensive coverage across multiple dimensions and perspectives.

## Historical Context
The topic has evolved significantly over time, with key developments shaping current understanding and applications.

## Current State Analysis
### Technical Aspects
- Core methodologies and approaches
- Implementation considerations
- Best practices and standards

### Market Dynamics
- Current trends and patterns
- Key stakeholders and influences
- Economic factors and implications

### Social Impact
- Community effects and considerations
- Accessibility and inclusion factors
- Long-term societal implications

## Comparative Analysis
### Advantages
1. Significant benefits for {target_audience} users
2. Proven effectiveness in real-world applications
3. Strong potential for future development

### Challenges
1. Implementation complexity considerations
2. Resource requirements and constraints
3. Adoption barriers and solutions

## Future Perspectives
### Short-term Outlook (1-2 years)
Expected developments and immediate opportunities for growth and improvement.

### Long-term Vision (3-5 years)
Strategic considerations and transformational potential across various sectors.

## Actionable Recommendations
1. **Immediate Actions**: Specific steps for quick implementation
2. **Medium-term Strategy**: Planned development and expansion phases
3. **Long-term Planning**: Strategic positioning and future-proofing

## Conclusion
The comprehensive analysis of "{content.strip()}" reveals significant potential for {target_audience} applications with clear pathways for successful implementation.

*Expanded content generated using mock AI topic expansion for testing purposes.*
"""
        else:  # GENERAL processing
            # Improve the original content
            improved_content = content.strip()
            if len(improved_content) < 100:
                improved_content = f"Enhanced version: {improved_content}"

            return f"""**Processed Content** ({voice} voice for {target_audience} audience):

{improved_content}

*[Content has been enhanced for clarity, style, and engagement while maintaining the original meaning and intent. This is mock processing for testing purposes.]*

**Key Improvements Made:**
- Enhanced clarity and readability
- Optimized for {target_audience} audience
- Applied {voice} writing voice
- Maintained original intent and meaning
- Improved structure and flow

*Generated using mock AI content processing for testing purposes.*
"""

    async def process_content(
        self,
        content: str,
        processing_type: str = "general",
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Mock content processing with realistic simulation.

        Returns:
            Tuple of (processed_content, quality_score, processing_metadata)
        """
        if options is None:
            options = {}

        # Simulate processing time
        processing_time = random.uniform(0.5, 3.0)
        await asyncio.sleep(processing_time)

        try:
            # Convert string to enum
            proc_type = ProcessingType(processing_type)
        except ValueError:
            proc_type = ProcessingType.GENERAL

        # Select model based on processing type (mock)
        model_selection = {
            ProcessingType.GENERAL: "gpt-3.5-turbo",
            ProcessingType.CONTENT_ANALYSIS: "gpt-3.5-turbo",
            ProcessingType.ARTICLE_GENERATION: "gpt-4-turbo",
            ProcessingType.TOPIC_EXPANSION: "gpt-4-turbo",
            ProcessingType.QUALITY_ASSESSMENT: "gpt-4",
        }
        model_used = model_selection.get(proc_type, "gpt-3.5-turbo")

        # Generate mock processed content
        processed_content = self._generate_mock_content(content, proc_type, options)

        # Calculate realistic mock metrics
        estimated_tokens = len(content) + len(processed_content)
        estimated_cost = (estimated_tokens / 1000) * self.model_configs[model_used][
            "cost_per_1k_tokens"
        ]
        quality_score = random.uniform(0.75, 0.95)
        region_used = self.model_configs[model_used]["region"]

        # Update mock statistics
        self.processing_stats["total_requests"] += 1
        self.processing_stats["successful_requests"] += 1
        self.processing_stats["total_cost"] += estimated_cost
        self.processing_stats["region_usage"][region_used] += 1

        # Build comprehensive metadata
        processing_metadata = {
            "processing_type": processing_type,
            "options": options,
            "model_used": model_used,
            "region": region_used,
            "processing_time": processing_time,
            "estimated_cost": estimated_cost,
            "token_usage": {
                "prompt_tokens": len(content) // 4,
                "completion_tokens": len(processed_content) // 4,
                "total_tokens": estimated_tokens // 4,
            },
            "quality_score": quality_score,
            "timestamp": time.time(),
            "status": "completed",
            "voice": options.get("voice", "professional"),
            "target_audience": options.get("target_audience", "general"),
            "mock_mode": True,  # Indicator that this is mock processing
        }

        logger.info(
            f"Mock content processed: type={processing_type}, quality={quality_score:.2f}, "
            f"model={model_used}, cost=${estimated_cost:.4f}"
        )

        return processed_content, quality_score, processing_metadata

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get mock processing statistics for monitoring."""
        return {
            **self.processing_stats,
            "success_rate": (
                self.processing_stats["successful_requests"]
                / max(self.processing_stats["total_requests"], 1)
            ),
            "average_cost_per_request": (
                self.processing_stats["total_cost"]
                / max(self.processing_stats["successful_requests"], 1)
            ),
            "mock_mode": True,
        }


# Global mock processor instance
mock_processor = MockContentProcessor()
