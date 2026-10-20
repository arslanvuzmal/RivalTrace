import json
import structlog
import anthropic
from app.core.config import settings
from app.schemas.insights import CompetitorInsight
from app.services.demo_insights import demo_insight
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)

def get_claude_client():
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured.")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are an expert Strategic Business Analyst. Your job is to read raw data 
representing the exact changes (delta) on a competitor's website over the last week. 
You must distill these changes into a high-level strategic briefing for executive leadership.

You MUST respond ONLY with a strictly formatted JSON object matching this schema:
{
  "executive_summary": "A 1-2 sentence high-level summary of the most important strategic shift.",
  "threat_level": "LOW|MEDIUM|HIGH",
  "what_changed": [
     {"category": "Pricing|Product|Marketing|Leadership|Other", "description": "Specific detail"}
  ],
  "what_it_means": [
     {"category": "Strategy|Market Position|Financials", "description": "Specific detail"}
  ],
  "what_to_do": [
     {"category": "Action|Monitor|Ignore", "description": "Specific detail"}
  ]
}
Do NOT wrap the JSON in Markdown backticks or provide any conversational text before or after."""

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.InternalServerError, Exception)),
    reraise=True
)
def _call_claude(competitor_name: str, sanitized_delta: str) -> CompetitorInsight:
    client = get_claude_client()
    
    logger.info("Calling Claude for insights", competitor_name=competitor_name)
    # claude-3-haiku-20240307 is retired. Current models think by default and the thinking counts
    # towards max_tokens, so 1024 could cut the JSON off.
    response = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Competitor Name: {competitor_name}\n\nWeekly Delta:\n{sanitized_delta}"
            }
        ]
    )

    if response.stop_reason == "refusal":
        raise ValueError("Claude declined to analyse this delta.")
    # A thinking block can come before the answer; read the first text block, not content[0].
    text_block = next((b for b in response.content if b.type == "text"), None)
    if text_block is None:
        raise ValueError("Claude returned no text.")
    raw_response = text_block.text.strip()
    # Attempt to clean up markdown if present despite prompt instructions
    if raw_response.startswith("```json"):
        raw_response = raw_response[7:-3].strip()
    
    parsed_json = json.loads(raw_response)
    return CompetitorInsight(**parsed_json)


def generate_strategic_insights(competitor_name: str, sanitized_delta: str) -> CompetitorInsight:
    """
    Sends the sanitized delta data to Claude and returns a structured CompetitorInsight object.
    Implements retries, and if it completely fails, returns a graceful fallback object.
    """
    if settings.demo_mode:
        return demo_insight(competitor_name, sanitized_delta)
    try:
        return _call_claude(competitor_name, sanitized_delta)
    except Exception as e:
        logger.error("Claude insights generation failed after retries", competitor_name=competitor_name, error=str(e))
        # Fallback Mechanism to prevent crushing the whole pipeline
        return CompetitorInsight(
            executive_summary="AI Analysis temporarily unavailable for this competitor.",
            threat_level="LOW",
            what_changed=[],
            what_it_means=[],
            what_to_do=[]
        )
