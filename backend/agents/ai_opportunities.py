import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, AIOpportunityOutput, AIOpportunity

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are an AI transformation strategist with deep expertise in telecommunications and OSS/BSS modernization.

You must return ONLY valid JSON — no markdown, no explanation, no preamble.

{
  "opportunities": [
    {
      "id": "AI-001",
      "title": "short opportunity title",
      "domain": "CRM | Billing | Provisioning | Inventory | Assurance | Cross-Domain",
      "opportunity_type": "automation | prediction | nlp | anomaly_detection | optimization | generative_ai",
      "description": "specific description referencing actual data/tables from the assets",
      "business_value": "quantified or specific business impact",
      "effort": "low | medium | high",
      "wave": 1
    }
  ],
  "summary": "3-4 sentence summary"
}

Rules:
- Ground every opportunity in data that actually exists in the assets
- Include at least one GenAI/LLM opportunity
- Wave: 1=quick win, 2=mid migration, 3=post-migration
- Aim for 8-10 high quality opportunities"""


def build_prompt(assets, discovery, risk):
    blocks = [f"=== {a.filename} ({a.asset_type}) ===\n{a.raw_summary}\n" for a in assets]
    ctx = ""
    if discovery:
        ctx += f"\nDISCOVERY: {discovery.summary}"
    if risk:
        top = [r.title for r in risk.risk_items[:5]]
        ctx += f"\nTOP RISKS: {', '.join(top)}"
    return f"""Identify AI/ML transformation opportunities from these telco assets.

{"".join(blocks)}{ctx}

Return ONLY the JSON object. No markdown, no explanation."""


async def run_ai_opportunities_agent(assets, discovery, risk):
    prompt = build_prompt(assets, discovery, risk)
    full_response = ""

    async with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        async for text in stream.text_stream:
            full_response += text
            yield {"type": "chunk", "text": text}

    try:
        clean = full_response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)
        data = json.loads(clean)
        opportunities = [AIOpportunity(**o) for o in data.get("opportunities", [])]
        result = AIOpportunityOutput(opportunities=opportunities, summary=data.get("summary", ""))
        yield {"type": "result", "data": result.model_dump()}
    except Exception as e:
        yield {"type": "error", "message": f"Failed to parse AI opportunities: {e}", "raw": full_response[:500]}
