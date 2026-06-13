import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, AIOpportunityOutput, AIOpportunity

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are an AI transformation strategist for telecom OSS/BSS modernization.

Return ONLY valid JSON:
{
  "opportunities": [{"id": "AI-001", "title": "title", "domain": "CRM|Billing|Provisioning|Inventory|Assurance|Cross-Domain", "opportunity_type": "automation|prediction|nlp|anomaly_detection|optimization|generative_ai", "description": "specific description", "business_value": "impact", "effort": "low|medium|high", "wave": 1}],
  "summary": "3-4 sentences"
}

Aim for 8-10 opportunities. Wave 1=quick win, 2=mid, 3=post-migration. Ground each in actual data from the assets."""


def build_prompt(assets, discovery, risk):
    blocks = [f"=== {a.filename} ===\n{a.raw_summary}\n" for a in assets]
    ctx = ""
    if discovery: ctx += f"\nDISCOVERY: {discovery.summary}"
    if risk: ctx += f"\nTOP RISKS: {', '.join(r.title for r in risk.risk_items[:5])}"
    return f"Identify AI/ML opportunities in this telco environment.\n\n{''.join(blocks)}{ctx}\n\nReturn ONLY JSON."


async def run_ai_opportunities_agent(assets, discovery, risk):
    prompt = build_prompt(assets, discovery, risk)
    print(f"[ai_opps] Starting Claude API call")
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = response.content[0].text
        print(f"[ai_opps] Got response, length={len(full_response)}")
        yield {"type": "chunk", "text": full_response}
    except Exception as e:
        print(f"[ai_opps] Claude API error: {e}")
        yield {"type": "error", "message": f"Claude API error: {e}"}
        return

    try:
        clean = full_response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)
        data = json.loads(clean)
        opps = [AIOpportunity(**o) for o in data.get("opportunities", [])]
        result = AIOpportunityOutput(opportunities=opps, summary=data.get("summary", ""))
        yield {"type": "result", "data": result.model_dump()}
    except Exception as e:
        print(f"[ai_opps] Parse error: {e}")
        yield {"type": "error", "message": f"Parse error: {e}"}
