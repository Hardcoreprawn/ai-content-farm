import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from models import RankedTopic, SourceData, GeneratedContent
from service_logic import ContentGeneratorService


class TestContentGeneratorService:
    """Test content generation service functionality"""

    @pytest.fixture
    def mock_topic(self):
        """Create a mock ranked topic"""
        return RankedTopic(
            topic="AI Infrastructure Investment",
            sources=[
                SourceData(
                    name="TechCrunch",
                    url="https://techcrunch.com/ai-investment",
                    title="UK Announces Major AI Investment",
                    summary="Government invests £2bn in AI infrastructure"
                ),
                SourceData(
                    name="The Register",
                    url="https://theregister.com/ai-data-centers",
                    title="New Data Centers for AI Workloads",
                    summary="Infrastructure to support AI development"
                )
            ],
            rank=1,
            ai_score=0.85,
            sentiment="positive",
            tags=["AI", "Investment", "Infrastructure"]
        )

    @pytest.fixture
    def service(self):
        """Create content generator service with mocked dependencies"""
        with patch('service_logic.BlobServiceClient'), \
                patch('service_logic.openai.AsyncOpenAI'), \
                patch('service_logic.anthropic.AsyncAnthropic'):
            service = ContentGeneratorService()
            service.openai_client = AsyncMock()
            service.claude_client = AsyncMock()
            service.blob_client = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_generate_shortform_content(self, service, mock_topic):
        """Test shortform content generation"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = """TITLE: UK's £2bn AI Investment: A Game Changer for Tech Innovation

CONTENT:
The UK government has announced a groundbreaking £2 billion investment in AI infrastructure, marking one of the most significant commitments to artificial intelligence development in European history. This massive funding initiative will establish state-of-the-art data centers in Manchester, Edinburgh, and Cardiff, positioning Britain as a global leader in AI innovation.

The investment comes at a critical time when nations worldwide are racing to dominate the AI landscape. By establishing dedicated AI infrastructure, the UK is not just keeping pace with competitors like China and the United States, but creating the foundation for sustained technological leadership.

This strategic move will attract international tech companies, create thousands of high-skilled jobs, and establish the UK as a preferred destination for AI research and development. The ripple effects will extend far beyond technology, influencing everything from healthcare innovation to financial services automation.

For businesses and investors, this represents a clear signal that the UK is serious about its AI ambitions, making it an attractive destination for AI-focused ventures and partnerships."""

        service.openai_client.chat.completions.create.return_value = mock_response

        result = await service.generate_content(mock_topic, "shortform")

        assert isinstance(result, GeneratedContent)
        assert result.content_type == "shortform"
        assert result.topic == "AI Infrastructure Investment"
        assert "UK's £2bn AI Investment" in result.title
        assert result.word_count > 0
        assert result.ai_model == "gpt-3.5-turbo"
        assert len(result.sources) == 2

    @pytest.mark.asyncio
    async def test_generate_briefing_content(self, service, mock_topic):
        """Test briefing content generation"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = """TITLE: UK AI Infrastructure Investment: Comprehensive Analysis of the £2bn Initiative

CONTENT:
# Executive Summary

The United Kingdom has announced a transformative £2 billion investment in artificial intelligence infrastructure, representing the largest single commitment to AI development in British history. This comprehensive briefing analyzes the initiative's scope, implications, and potential impact on the global AI landscape.

# Background and Context

The announcement comes amid intensifying global competition in artificial intelligence, with major powers including the United States, China, and the European Union making substantial investments in AI capabilities. The UK's £2 billion commitment demonstrates its determination to remain competitive in this critical technology sector.

# Investment Details

The funding will be allocated across three primary areas:
- Data center infrastructure in Manchester, Edinburgh, and Cardiff
- Research and development facilities
- Skills training and education programs

Each facility will feature cutting-edge hardware optimized for AI workloads, including the latest GPU clusters and quantum computing interfaces.

# Strategic Implications

This investment positions the UK as a serious contender in the global AI race, potentially attracting significant private sector investment and international partnerships. The geographic distribution across England, Scotland, and Wales ensures broad regional benefits.

# Economic Impact

Conservative estimates suggest the initiative will create over 10,000 direct jobs and potentially 50,000 indirect positions across the technology sector. The economic multiplier effects could contribute billions to GDP over the next decade.

# International Competitiveness

By establishing world-class AI infrastructure, the UK is addressing one of the key barriers to AI innovation: access to computational resources. This puts British researchers and companies on par with their international counterparts.

# Conclusion

The £2 billion AI infrastructure investment represents a pivotal moment for UK technology policy, with the potential to establish Britain as a global AI superpower for generations to come."""

        service.openai_client.chat.completions.create.return_value = mock_response

        result = await service.generate_content(mock_topic, "briefing")

        assert isinstance(result, GeneratedContent)
        assert result.content_type == "briefing"
        assert result.word_count > 500  # Should be longer than shortform
        assert result.ai_model == "gpt-4"
        assert "Comprehensive Analysis" in result.title

    @pytest.mark.asyncio
    async def test_generate_deepdive_content(self, service, mock_topic):
        """Test deep dive content generation"""
        # Mock Claude response
        mock_response = MagicMock()
        mock_response.content[0].text = """TITLE: The UK's £2bn AI Infrastructure Investment: A Strategic Analysis of Britain's Bid for AI Supremacy

CONTENT:
# Abstract

This analysis examines the United Kingdom's £2 billion artificial intelligence infrastructure investment, evaluating its strategic positioning, technical specifications, economic implications, and competitive dynamics within the global AI landscape. Through comprehensive analysis of policy documents, technical specifications, and comparative international approaches, this study assesses the initiative's potential to establish the UK as a leading AI development hub.

# Introduction

The global artificial intelligence landscape has reached an inflection point where national competitiveness increasingly depends on AI capabilities. The UK's announcement of a £2 billion AI infrastructure investment represents not merely a financial commitment, but a strategic repositioning in the international technology hierarchy.

# Methodology

This analysis employs a multi-faceted approach, examining:
- Technical infrastructure specifications
- Economic impact modeling
- Competitive positioning analysis
- Historical precedent evaluation
- Policy framework assessment

# Historical Context and Evolution

The UK's AI ambitions trace back to the 2017 AI Sector Deal, which allocated £300 million to AI development. This new £2 billion commitment represents a seven-fold increase, reflecting both the escalating importance of AI and the intensifying global competition.

# Technical Infrastructure Analysis

The proposed data centers in Manchester, Edinburgh, and Cardiff will feature:
- Advanced GPU clusters optimized for machine learning workloads
- High-speed networking infrastructure enabling distributed computing
- Quantum computing integration capabilities
- Energy-efficient cooling systems reducing operational costs

# Economic Impact Modeling

Conservative projections suggest the investment will generate:
- Direct employment: 12,000-15,000 high-skilled positions
- Indirect employment: 40,000-60,000 additional jobs
- GDP contribution: £8-12 billion over the next decade
- Private sector leverage: 3:1 ratio of private investment

# International Competitive Dynamics

The UK's £2 billion commitment must be evaluated against comparable international investments:
- United States: $50+ billion in CHIPS Act AI provisions
- China: Estimated $70+ billion in AI infrastructure (2021-2025)
- European Union: €43 billion Digital Europe Programme

While smaller in absolute terms, the UK's focused approach may yield higher per-capita returns and more concentrated innovation benefits.

# Regional Development Implications

The geographic distribution across Manchester, Edinburgh, and Cardiff reflects a deliberate strategy to:
- Leverage existing technology clusters
- Ensure equitable regional development
- Tap into diverse talent pools
- Reduce dependence on London-centric innovation

# Technological Capabilities and Specifications

Each facility will incorporate state-of-the-art technologies:
- NVIDIA H100 and future-generation AI accelerators
- 400Gb/s networking infrastructure
- Liquid cooling systems achieving PUE ratios below 1.2
- Integration with renewable energy sources

# Skills Development and Human Capital

A critical component of the investment addresses the AI skills gap through:
- University partnership programs
- Industry-academic collaboration initiatives
- Continuing education for technology professionals
- International talent attraction schemes

# Policy Framework and Governance

The initiative operates within a broader policy framework encompassing:
- AI ethics and safety regulations
- Data protection and privacy safeguards
- International cooperation agreements
- Innovation sandbox programs

# Risk Assessment and Mitigation

Potential challenges include:
- Technology obsolescence risks
- International talent competition
- Regulatory compliance complexities
- Economic volatility impacts

# Future Scenarios and Projections

Three potential outcomes emerge:
1. Optimal scenario: UK becomes Europe's AI development hub
2. Moderate scenario: Competitive positioning with peer nations
3. Suboptimal scenario: Limited differentiation from existing capabilities

# Conclusion

The UK's £2 billion AI infrastructure investment represents a calculated strategic gamble with the potential for transformative national benefits. Success will depend on execution quality, international cooperation, and continued political commitment across electoral cycles."""

        service.claude_client.messages.create.return_value = mock_response

        result = await service.generate_content(mock_topic, "deepdive")

        assert isinstance(result, GeneratedContent)
        assert result.content_type == "deepdive"
        assert result.word_count > 1000  # Should be much longer
        assert result.ai_model == "claude-3-sonnet"
        assert "Strategic Analysis" in result.title

    def test_build_shortform_prompt(self, service, mock_topic):
        """Test shortform prompt construction"""
        prompt = service._build_shortform_prompt(mock_topic)

        assert "AI Infrastructure Investment" in prompt
        assert "500-800 word" in prompt
        assert "TechCrunch" in prompt
        assert "The Register" in prompt
        assert "TITLE:" in prompt
        assert "CONTENT:" in prompt

    def test_build_briefing_prompt(self, service, mock_topic):
        """Test briefing prompt construction"""
        prompt = service._build_briefing_prompt(mock_topic)

        assert "3000-word" in prompt
        assert "comprehensive" in prompt
        assert "Executive summary" in prompt
        assert mock_topic.topic in prompt

    def test_build_deepdive_prompt(self, service, mock_topic):
        """Test deep dive prompt construction"""
        prompt = service._build_deepdive_prompt(mock_topic)

        assert "5000+" in prompt
        assert "analytical" in prompt
        assert "Abstract" in prompt
        assert "methodology" in prompt

    def test_parse_ai_response_with_format(self, service):
        """Test parsing formatted AI response"""
        response = """TITLE: Test Article Title

CONTENT:
This is the content of the article.
It has multiple lines and paragraphs.

This is another paragraph."""

        title, content = service._parse_ai_response(response)

        assert title == "Test Article Title"
        assert "This is the content" in content
        assert "another paragraph" in content

    def test_parse_ai_response_fallback(self, service):
        """Test parsing unformatted AI response"""
        response = """# Test Article Title
This is the content without proper formatting.
It should still work."""

        title, content = service._parse_ai_response(response)

        assert title == "Test Article Title"
        assert "This is the content" in content
