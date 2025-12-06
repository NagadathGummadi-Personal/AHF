"""
Real-time Azure GPT-4.1 Mini Structured Output Tests.

Run these tests manually with real Azure credentials to verify
structured JSON output works with the actual API.

Setup:
    $env:AZURE_OPENAI_KEY="your-api-key"
    $env:AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
    $env:AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"

Run:
    uv run pytest tests/llms/test_azure_structured_output_realtime.py::test_quick_demo_structured_output -v -s

Logs:
    All test output is logged to: logs/structured_output_tests.log
"""

import json
import pytest
import os
from typing import List
from pydantic import BaseModel, Field

from core.llms import LLMFactory
from core.llms.spec.llm_context import create_context
from utils.logging.LoggerAdaptor import LoggerAdaptor
from utils.converters import parse_streaming_json
from utils.converters.partial_json_parser import parse_partial_json
import logging

# Set up dedicated log file for structured output tests
log_file_path = 'logs/structured_output_realtime.log'
file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Configure logger for these tests
logger = LoggerAdaptor.get_logger("tests.llms.structured_output_realtime")

# Add file handler to the logger
if hasattr(logger, 'logger') and logger.logger:
    logger.logger.addHandler(file_handler)
    logger.logger.setLevel(logging.DEBUG)

# Also add handler to LLM logger to capture those logs too
llm_logger = LoggerAdaptor.get_logger("llm.azure-gpt-4.1-mini")
if hasattr(llm_logger, 'logger') and llm_logger.logger:
    llm_logger.logger.addHandler(file_handler)
    llm_logger.logger.setLevel(logging.DEBUG)

logger.info(f"Logging configured - writing to: {log_file_path}")

AZURE_CONFIG = {
    "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource.openai.azure.com/"),
    "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
    "api_version": "2024-08-01-preview",  # Required for structured output (json_schema)
    "timeout": 60,
    "api_key": os.getenv("AZURE_OPENAI_KEY", ""),  # Set via environment variable
}

# ============================================================================
# Pydantic Response Schemas
# ============================================================================

class MovieRecommendation(BaseModel):
    """Movie recommendation response."""
    title: str = Field(description="Movie title : End with [Movie Title]")
    genre: str = Field(description="Movie genre")
    year: int = Field(ge=1900, le=2030, description="Release year")
    rating: float = Field(ge=0.0, le=10.0, description="Rating out of 10")
    synopsis: str = Field(description="Brief synopsis")
    reasons: List[str] = Field(description="Why this movie is recommended")


class EmailResponse(BaseModel):
    """Professional email response."""
    subject: str = Field(description="Email subject line")
    greeting: str = Field(description="Email greeting")
    body: str = Field(description="Email body content")
    closing: str = Field(description="Email closing")
    tone: str = Field(description="professional, friendly, or formal")
    urgency: str = Field(description="low, medium, or high")


class CodeAnalysis(BaseModel):
    """Code analysis response."""
    language: str = Field(description="Programming language")
    complexity: str = Field(description="low, medium, or high")
    issues: List[str] = Field(description="List of potential issues")
    suggestions: List[str] = Field(description="Improvement suggestions")
    securityConcerns: List[str] = Field(description="Security-related concerns")
    overallScore: float = Field(ge=0.0, le=100.0, description="Code quality score 0-100")


class ProductReview(BaseModel):
    """Product review analysis."""
    productName: str = Field(description="Product name")
    overallSentiment: str = Field(description="positive, negative, or mixed")
    rating: int = Field(ge=1, le=5, description="Star rating 1-5")
    pros: List[str] = Field(description="Positive aspects")
    cons: List[str] = Field(description="Negative aspects")
    recommendation: str = Field(description="would_buy, would_not_buy, or maybe")
    summary: str = Field(description="One-sentence summary")


# ============================================================================
# Test Setup
# ============================================================================

@pytest.fixture
def skip_if_no_credentials():
    """Skip tests if Azure credentials are not available."""
    if not all([
        AZURE_CONFIG["api_key"],
        AZURE_CONFIG["endpoint"],
        AZURE_CONFIG["deployment_name"]
    ]):
        pytest.skip("Azure credentials not found. Set AZURE_CONFIG['api_key'], AZURE_CONFIG['endpoint'], AZURE_CONFIG['deployment_name']")


@pytest.fixture
async def azure_llm():
    """Create real Azure LLM instance."""
    llm = LLMFactory.create_llm(
        "azure-gpt-4.1-mini",
        connector_config=AZURE_CONFIG
    )
    
    yield llm
    
    # Cleanup
    if hasattr(llm.connector, 'close'):
        await llm.connector.close()


@pytest.fixture
def test_context():
    """Create test context."""
    return create_context(user_id="realtime-test", session_id="structured-output")


# ============================================================================
# Quick Demo - Run This First!
# ============================================================================

@pytest.mark.asyncio  
async def test_quick_demo_structured_output(skip_if_no_credentials, azure_llm, test_context):
    """Quick demo showing structured output in action. Run this first!"""
    logger.info("="*100)
    logger.info("STRUCTURED OUTPUT DEMO - Movie Recommendation")
    logger.info("="*100)
    
    logger.info("Requesting movie recommendation with structured output schema")
    logger.info("Schema: MovieRecommendation (title, genre, year, rating, synopsis, reasons)")
    
    # Make request
    response = await azure_llm.get_answer(
        [{"role": "user", "content": "Recommend an epic sci-fi movie"}],
        test_context,
        response_format=MovieRecommendation,
        max_tokens=300
    )
    
    logger.info("-"*100)
    logger.info("RAW JSON RESPONSE from GPT-4.1 Mini")
    logger.info("Raw JSON", json_content=json.loads(response.content))
    
    movie = response.metadata["structured_output"]
    
    logger.info("-"*100)
    logger.info("VALIDATED PYDANTIC OBJECT")
    logger.info("Movie Recommendation",
                title=movie.title,
                year=movie.year,
                genre=movie.genre,
                rating=f"{movie.rating}/10",
                synopsis=movie.synopsis)
    
    for i, reason in enumerate(movie.reasons, 1):
        logger.info(f"Reason {i}", reason=reason)
    
    logger.info("-"*100)
    logger.info("API Usage Statistics",
                tokens=response.usage.total_tokens,
                cost=f"${response.usage.cost_usd:.6f}" if response.usage.cost_usd else "N/A",
                validation_status=response.metadata['validation_status'])
    logger.info("="*100)
    
    assert isinstance(movie, MovieRecommendation)
    assert movie.rating >= 0 and movie.rating <= 10
    assert movie.year >= 1900


# ============================================================================
# Real-time Structured Output Tests
# ============================================================================

@pytest.mark.asyncio
async def test_movie_recommendation_structured_output(skip_if_no_credentials, azure_llm, test_context):
    """Test getting structured movie recommendation."""
    logger.info("="*80)
    logger.info("TEST: Movie Recommendation with Structured Output")
    logger.info("="*80)
    
    messages = [{
        "role": "user",
        "content": "Recommend a sci-fi movie from the 2010s"
    }]
    
    response = await azure_llm.get_answer(
        messages,
        test_context,
        response_format=MovieRecommendation,
        max_tokens=300
    )
    
    logger.info("Raw Response", content=response.content)
    
    assert "structured_output" in response.metadata
    assert response.metadata["validation_status"] == "success"
    
    movie = response.metadata["structured_output"]
    assert isinstance(movie, MovieRecommendation)
    
    logger.info("[OK] Validated MovieRecommendation",
                title=movie.title,
                genre=movie.genre,
                year=movie.year,
                rating=movie.rating,
                synopsis=movie.synopsis,
                reasons=movie.reasons,
                tokens=response.usage.total_tokens,
                cost=response.usage.cost_usd)
    logger.info("="*80)


@pytest.mark.asyncio
async def test_email_response_structured_output(skip_if_no_credentials, azure_llm, test_context):
    """Test generating structured email response."""
    logger.info("="*80)
    logger.info("TEST: Email Response with Structured Output")
    logger.info("="*80)
    
    messages = [{
        "role": "user",
        "content": "Generate a professional email declining a meeting request politely"
    }]
    
    response = await azure_llm.get_answer(
        messages,
        test_context,
        response_format=EmailResponse,
        max_tokens=250
    )
    
    logger.info("Raw JSON Response", json_content=json.loads(response.content))
    
    email = response.metadata["structured_output"]
    assert isinstance(email, EmailResponse)
    
    logger.info("[OK] Validated EmailResponse",
                subject=email.subject,
                greeting=email.greeting,
                body=email.body,
                closing=email.closing,
                tone=email.tone,
                urgency=email.urgency)
    logger.info("="*80)


@pytest.mark.asyncio
async def test_code_analysis_structured_output(skip_if_no_credentials, azure_llm, test_context):
    """Test code analysis with structured output."""
    logger.info("="*80)
    logger.info("TEST: Code Analysis with Structured Output")
    logger.info("="*80)
    
    code_sample = """
def process_payment(amount, card_number):
    if amount > 0:
        charge_card(card_number, amount)
        return True
    return False
"""
    
    messages = [{
        "role": "user",
        "content": f"Analyze this Python code for issues:\n{code_sample}"
    }]
    
    response = await azure_llm.get_answer(
        messages,
        test_context,
        response_format=CodeAnalysis,
        max_tokens=400
    )
    
    logger.info("Raw JSON Response", json_content=json.loads(response.content))
    
    analysis = response.metadata["structured_output"]
    assert isinstance(analysis, CodeAnalysis)
    
    logger.info("[OK] Validated CodeAnalysis",
                language=analysis.language,
                complexity=analysis.complexity,
                quality_score=f"{analysis.overallScore}/100",
                issues=analysis.issues,
                suggestions=analysis.suggestions,
                security_concerns=analysis.securityConcerns,
                tokens=response.usage.total_tokens)
    logger.info("="*80)


@pytest.mark.asyncio
async def test_product_review_structured_output(skip_if_no_credentials, azure_llm, test_context):
    """Test product review analysis with structured output."""
    logger.info("="*80)
    logger.info("TEST: Product Review Analysis with Structured Output")
    logger.info("="*80)
    
    review_text = """
    This laptop is amazing! The battery lasts all day and the screen is gorgeous.
    However, it's quite expensive and the keyboard feels a bit mushy.
    Overall, I'm happy with the purchase but wish it was more affordable.
    """
    
    messages = [{
        "role": "user",
        "content": f"Analyze this product review:\n{review_text}"
    }]
    
    response = await azure_llm.get_answer(
        messages,
        test_context,
        response_format=ProductReview,
        max_tokens=300
    )
    
    logger.info("Raw JSON Response", json_content=json.loads(response.content))
    
    review = response.metadata["structured_output"]
    assert isinstance(review, ProductReview)
    
    logger.info("[OK] Validated ProductReview",
                product=review.productName,
                sentiment=review.overallSentiment,
                rating=f"{review.rating}/5",
                recommendation=review.recommendation,
                summary=review.summary,
                pros=review.pros,
                cons=review.cons)
    logger.info("="*80)


# ============================================================================
# Streaming Structured Output Test
# ============================================================================

@pytest.mark.asyncio
async def test_streaming_structured_output_realtime(skip_if_no_credentials, azure_llm, test_context):
    """Test streaming with structured output validation."""
    logger.info("="*80)
    logger.info("TEST: Streaming with Structured Output")
    logger.info("="*80)
    
    messages = [{
        "role": "user",
        "content": "Recommend a classic science fiction movie"
    }]
    
    logger.info("[STREAM] Starting streaming response...")
    
    chunks_received = 0
    accumulated_text = ""
    final_validated = None
    last_valid_partial = None
    validation_attempts = 0
    successful_validations = 0
    
    async for chunk in azure_llm.stream_answer(
        messages,
        test_context,
        response_format=MovieRecommendation,
        max_tokens=300
    ):
        chunks_received += 1
        
        if chunk.content:
            accumulated_text += chunk.content
            
            # Try to parse partial JSON every 5 chunks (to avoid spamming logs)
            if chunks_received % 5 == 0:
                validation_attempts += 1
                
                # Attempt 1: Parse as partial/incomplete JSON
                partial_data = parse_partial_json(accumulated_text)
                if partial_data:
                    logger.info(f"[CHUNK {chunks_received}] Partial JSON parsed",
                               length=len(accumulated_text),
                               keys=list(partial_data.keys()) if isinstance(partial_data, dict) else "non-dict")
                
                # Attempt 2: Try full validation with Pydantic
                try:
                    validated = parse_streaming_json(accumulated_text, MovieRecommendation)
                    if validated:
                        last_valid_partial = validated
                        successful_validations += 1
                        logger.info(f"[CHUNK {chunks_received}] [VALID] Pydantic validation successful!",
                                   title=validated.title if hasattr(validated, 'title') else 'N/A',
                                   progress=f"{len(accumulated_text)} chars")
                except Exception as e:
                    logger.debug(f"[CHUNK {chunks_received}] Validation not ready",
                                error=str(e)[:50])
        
        if chunk.is_final:
            logger.info("Stream completed",
                       total_chunks=chunks_received,
                       accumulated_length=len(accumulated_text),
                       validation_attempts=validation_attempts,
                       successful_partial_validations=successful_validations)
            
            if "structured_output" in chunk.metadata:
                final_validated = chunk.metadata["structured_output"]
                logger.info("Final structured output validation",
                           status=chunk.metadata['validation_status'])
            
            if chunk.usage:
                logger.info("Stream usage",
                           tokens=chunk.usage.total_tokens)
    
    assert final_validated is not None
    assert isinstance(final_validated, MovieRecommendation)
    
    logger.info("[OK] Final Validated Movie",
                title=final_validated.title,
                genre=final_validated.genre,
                year=final_validated.year,
                rating=final_validated.rating)
    
    logger.info("Validation Summary",
                total_chunks=chunks_received,
                validation_attempts=validation_attempts,
                successful_partial_validations=successful_validations,
                final_validation="SUCCESS")
    logger.info("="*80)


@pytest.mark.asyncio
async def test_partial_json_validation_during_streaming(skip_if_no_credentials, azure_llm, test_context):
    """Test progressive partial JSON validation during streaming."""
    logger.info("="*80)
    logger.info("TEST: Progressive Partial JSON Validation During Streaming")
    logger.info("="*80)
    
    messages = [{
        "role": "user",
        "content": "Recommend a horror movie from the 2020s with detailed reasons"
    }]
    
    logger.info("[STREAM] Starting streaming response with detailed validation...")
    
    accumulated_text = ""
    validation_timeline = []
    
    async for chunk in azure_llm.stream_answer(
        messages,
        test_context,
        response_format=MovieRecommendation,
        max_tokens=350
    ):
        if chunk.content:
            accumulated_text += chunk.content
            
            # Parse partial JSON on every chunk to see progression
            partial_data = parse_partial_json(accumulated_text)
            
            # Track what fields are becoming available
            fields_available = []
            if partial_data and isinstance(partial_data, dict):
                fields_available = list(partial_data.keys())
            
            # Try Pydantic validation
            validation_status = "incomplete"
            validated_obj = None
            try:
                validated_obj = parse_streaming_json(accumulated_text, MovieRecommendation)
                if validated_obj:
                    validation_status = "valid"
            except Exception:
                validation_status = "incomplete"
            
            validation_timeline.append({
                'length': len(accumulated_text),
                'fields': fields_available,
                'status': validation_status,
                'has_title': 'title' in fields_available,
                'has_reasons': 'reasons' in fields_available,
            })
            
            # Log every 10 chunks
            if len(validation_timeline) % 10 == 0:
                entry = validation_timeline[-1]
                logger.info(f"[Chunk #{len(validation_timeline)}]",
                           chars=entry['length'],
                           fields=entry['fields'],
                           status=entry['status'])
        
        if chunk.is_final:
            break
    
    # Analyze the validation timeline
    logger.info("-"*80)
    logger.info("VALIDATION TIMELINE ANALYSIS")
    
    first_title_at = next((i for i, e in enumerate(validation_timeline) if e['has_title']), None)
    first_valid_at = next((i for i, e in enumerate(validation_timeline) if e['status'] == 'valid'), None)
    first_reasons_at = next((i for i, e in enumerate(validation_timeline) if e['has_reasons']), None)
    
    logger.info("Key Milestones",
               first_title_appeared_at_chunk=first_title_at,
               first_reasons_appeared_at_chunk=first_reasons_at,
               first_fully_valid_at_chunk=first_valid_at,
               total_chunks=len(validation_timeline))
    
    # Show field progression
    if first_title_at:
        logger.info(f"Title appeared after {validation_timeline[first_title_at]['length']} characters")
    
    if first_valid_at:
        logger.info(f"Full validation succeeded after {validation_timeline[first_valid_at]['length']} characters")
        final_fields = validation_timeline[first_valid_at]['fields']
        logger.info(f"Fields at first validation: {final_fields}")
    
    # Show last few entries to see progression
    logger.info("-"*80)
    logger.info("LAST 5 VALIDATION ATTEMPTS:")
    for i, entry in enumerate(validation_timeline[-5:], len(validation_timeline)-4):
        logger.info(f"  [{i}] {entry['length']} chars | Fields: {entry['fields']} | Status: {entry['status']}")
    
    logger.info("="*80)
    
    # Assertions
    assert len(validation_timeline) > 0
    assert first_valid_at is not None, "Should eventually get a valid JSON"


# ============================================================================
# Text vs JSON Mode Comparison
# ============================================================================

@pytest.mark.asyncio
async def test_text_vs_json_mode_comparison(skip_if_no_credentials, azure_llm, test_context):
    """Compare text mode vs JSON structured output mode."""
    logger.info("="*80)
    logger.info("TEST: Text Mode vs JSON Structured Output Comparison")
    logger.info("="*80)
    
    prompt = "Recommend a good action movie from 2020-2024"
    messages = [{"role": "user", "content": prompt}]
    
    # Test 1: Regular text mode
    logger.info("[1] TEXT MODE (no schema)")
    
    text_response = await azure_llm.get_answer(
        messages,
        test_context,
        max_tokens=200
    )
    
    logger.info("Text Response",
                content=text_response.content,
                content_type=str(type(text_response.content)),
                has_structured=('structured_output' in text_response.metadata))
    
    # Test 2: JSON structured output mode
    logger.info("[2] JSON MODE (with MovieRecommendation schema)")
    
    json_response = await azure_llm.get_answer(
        messages,
        test_context,
        response_format=MovieRecommendation,
        max_tokens=300
    )
    
    logger.info("JSON Response", json_content=json.loads(json_response.content))
    
    movie = json_response.metadata["structured_output"]
    logger.info("[OK] Validated Movie Object",
                title=movie.title,
                genre=movie.genre,
                year=movie.year,
                rating=movie.rating)
    
    # Verify differences
    assert isinstance(text_response.content, str)
    assert isinstance(json_response.content, str)
    assert "structured_output" in json_response.metadata
    assert json_response.metadata["validation_status"] == "success"
    
    logger.info("="*80)


# ============================================================================
# Vision + Structured Output Test
# ============================================================================

@pytest.mark.asyncio
async def test_vision_with_structured_output_realtime(skip_if_no_credentials, azure_llm, test_context):
    """Test vision input with structured JSON output."""
    logger.info("="*80)
    logger.info("TEST: Vision Input + Structured JSON Output")
    logger.info("="*80)
    
    class DetailedImageAnalysis(BaseModel):
        """Detailed image analysis."""
        mainSubject: str
        setting: str
        objects: List[str]
        colors: List[str]
        mood: str
        timeOfDay: str
        weatherCondition: str
        estimatedLocation: str
    
    # Using a reliable Wikipedia image URL that's publicly accessible
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/300px-PNG_transparency_demonstration_1.png"
    
    logger.info("[IMAGE]  Analyzing Image", image_url=image_url)
    
    response = await azure_llm.get_answer_with_vision(
        prompt="Analyze this image in detail",
        images=[image_url],
        ctx=test_context,
        response_format=DetailedImageAnalysis,
        max_tokens=350
    )
    
    logger.info("Raw JSON Response", json_content=json.loads(response.content))
    
    analysis = response.metadata["structured_output"]
    assert isinstance(analysis, DetailedImageAnalysis)
    
    logger.info("[OK] Validated Image Analysis",
                main_subject=analysis.mainSubject,
                setting=analysis.setting,
                objects=analysis.objects,
                colors=analysis.colors,
                mood=analysis.mood,
                time_of_day=analysis.timeOfDay,
                weather=analysis.weatherCondition,
                location=analysis.estimatedLocation,
                tokens=response.usage.total_tokens)
    logger.info("="*80)


# ============================================================================
# Comprehensive Workflow Test
# ============================================================================

@pytest.mark.asyncio
async def test_complete_structured_output_workflow(skip_if_no_credentials, azure_llm, test_context):
    """Comprehensive test demonstrating all structured output features."""
    logger.info("="*80)
    logger.info("COMPREHENSIVE TEST: Complete Structured Output Workflow")
    logger.info("="*80)
    
    test_results = {
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0
    }
    
    # Test 1: Non-streaming with schema
    logger.info("[1] Non-Streaming + Structured Output")
    try:
        response = await azure_llm.get_answer(
            [{"role": "user", "content": "Recommend an action movie"}],
            test_context,
            response_format=MovieRecommendation,
            max_tokens=250
        )
        
        assert "structured_output" in response.metadata
        movie = response.metadata["structured_output"]
        logger.info("✓ Success", movie_title=movie.title)
        test_results["tests_passed"] += 1
    except Exception as e:
        logger.error("✗ Failed", error=str(e))
        test_results["tests_failed"] += 1
    finally:
        test_results["tests_run"] += 1
    
    # Test 2: Streaming with schema
    logger.info("[2] Streaming + Structured Output")
    try:
        final_chunk = None
        async for chunk in azure_llm.stream_answer(
            [{"role": "user", "content": "Recommend a drama movie"}],
            test_context,
            response_format=MovieRecommendation,
            max_tokens=250
        ):
            if chunk.is_final:
                final_chunk = chunk
        
        assert final_chunk is not None
        assert "structured_output" in final_chunk.metadata
        movie = final_chunk.metadata["structured_output"]
        logger.info("✓ Success (streaming)", movie_title=movie.title)
        test_results["tests_passed"] += 1
    except Exception as e:
        logger.error("✗ Failed", error=str(e))
        test_results["tests_failed"] += 1
    finally:
        test_results["tests_run"] += 1
    
    # Test 3: Regular text (no schema)
    logger.info("[3] Regular Text Output (no schema)")
    try:
        response = await azure_llm.get_answer(
            [{"role": "user", "content": "Say hello"}],
            test_context,
            max_tokens=50
        )
        
        assert isinstance(response.content, str)
        logger.info("✓ Success (text mode)", content_preview=response.content[:50])
        test_results["tests_passed"] += 1
    except Exception as e:
        logger.error("✗ Failed", error=str(e))
        test_results["tests_failed"] += 1
    finally:
        test_results["tests_run"] += 1
    
    # Test 4: Multiple schemas sequentially
    logger.info("[4] Multiple Different Schemas")
    try:
        r1 = await azure_llm.get_answer(
            [{"role": "user", "content": "Write email accepting invitation"}],
            test_context,
            response_format=EmailResponse,
            max_tokens=200
        )
        
        r2 = await azure_llm.get_answer(
            [{"role": "user", "content": "Recommend a movie"}],
            test_context,
            response_format=MovieRecommendation,
            max_tokens=200
        )
        
        email = r1.metadata["structured_output"]
        movie = r2.metadata["structured_output"]
        
        assert isinstance(email, EmailResponse)
        assert isinstance(movie, MovieRecommendation)
        logger.info("✓ Success (multiple schemas)",
                   email_tone=email.tone,
                   movie_title=movie.title)
        test_results["tests_passed"] += 1
    except Exception as e:
        logger.error("✗ Failed", error=str(e))
        test_results["tests_failed"] += 1
    finally:
        test_results["tests_run"] += 1
    
    # Summary
    logger.info("="*80)
    logger.info("WORKFLOW TEST SUMMARY",
                tests_run=test_results['tests_run'],
                passed=test_results['tests_passed'],
                failed=test_results['tests_failed'])
    logger.info("="*80)
    
    assert test_results["tests_failed"] == 0, f"{test_results['tests_failed']} tests failed"
