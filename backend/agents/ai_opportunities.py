"""
Agent 3: AI Opportunity Identifier
Scans the telco environment for high-value AI/ML automation
and optimization opportunities per domain.
"""

import json
import re
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, AIOpportunityOutput, AIOpportunity

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an AI transformation strategist with deep expertise in telecommunications and OSS/BSS modernization.
You identify practical, high-value AI and machine learning opportunities within legacy telecom environments.

Analyze the provided technical assets, discovery map, and risk findings to identify specific AI/ML opportunities
that can be implemented as part of or alongside the modernization journey.

You must return ONLY valid JSON — no markdown, no explanation, no preamble.

The JSON must exactly match this structure:

{
  "opportunities": [
    {
      "id": "AI-001",
      "title": "short opportunity title",
      "domain": "CRM | Billing | Provisioning | Inventory | Assurance | Cross-Domain",
      "opportunity_type": "automation | prediction | nlp | anomaly_detection | optimization | generative_ai",
      "description": "specific description — what data exists, what model/approach, what it replaces",
      "business_value": "quantified or specific business impact",
      "effort": "low | medium | high",
      "wave": 1 | 2 | 3
    }
  ],
  "summary": "3-4 sentence summary of the AI opportunity landscape"
}

Rules:
- Be specific — reference actual tables, fields, and data volumes from the assets
- Every opportunity must be grounded in data that actually exists in the ingested assets
- Prioritize opportunities that UNBLOCK or ACCELERATE the modernization (not just nice-to-haves)
- Include at least one GenAI/LLM opportunity (e.g. for fallout analysis, documentation generation)
- The churn score in CUSTOMER_SEGMENT is stale and model-drifted — flag an ML refresh opportunity
- Unrated CDRs, dunning logic in PL/SQL, manual reconciliation are all automation targets
- Wave assignment: 1=quick win/low dependency, 2=mid migration, 3=post-migration optimization
- aim for 8-12 high quality opportunities"""


def build_prompt(assets: list[ParsedAsset], discovery: DiscoveryOutput | None, risk: RiskOutput | None) -> str:
    asset_blocks = []
    for asset in assets:
        asset_blocks.append(f"=== {asset.filename} ({asset.asset_type}) ===\n{asset.raw_summary}\n")

    context_blocks = []
    if discovery:
        context_blocks.append(f"DISCOVERY SUMMARY:\n{discovery.summary}")
    if risk:
        top_risks = [r.title for r in risk.risk_items[:8]]
        context_blocks.append(f"TOP RISKS IDENTIFIED:\n" + "\n".join(f"  - {r}" for r in top_risks))

    return f"""Analyze these telco assets and identify AI/ML transformation opportunities.

{"".join(asset_blocks)}

{chr(10).join(context_blocks)}

Return ONLY the JSON object. No markdown, no explanation."""


async def run_ai_opportunities_agent(
    assets: list[ParsedAsset],
    discovery: DiscoveryOutput | None,
    risk: RiskOutput | None
):
    """
    Streams AI opportunity analysis. Yields chunks then final AIOpportunityOutput.
    """
    prompt = build_prompt(assets, discovery, risk)
    full_response = ""

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            full_response += text
            yield {"type": "chunk", "text": text}

    try:
        clean = full_response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)

        data = json.loads(clean)
        opportunities = [AIOpportunity(**o) for o in data.get("opportunities", [])]
        result = AIOpportunityOutput(
            opportunities=opportunities,
            summary=data.get("summary", "")
        )
        yield {"type": "result", "data": result.model_dump()}
    except Exception as e:
        yield {"type": "error", "message": f"Failed to parse AI opportunities output: {e}", "raw": full_response[:500]}
