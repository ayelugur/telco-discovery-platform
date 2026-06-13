import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, RiskItem

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a principal architect specializing in telecom modernization risk assessment.

Return ONLY valid JSON:
{
  "risk_items": [{"id": "RISK-001", "system": "name", "category": "Circular Dependency|Data Ownership|API Coverage|Batch Risk|Security|Compliance|Performance|Data Quality", "title": "title", "description": "detail", "severity": "low|medium|high|critical", "impact": "business impact", "recommendation": "fix"}],
  "heatmap": [{"system": "name", "category": "category", "score": 0, "label": "label", "risk_ids": ["RISK-001"]}],
  "overall_risk_score": 0,
  "summary": "3-4 sentences"
}

Systems: Amdocs CRM, Netcracker, Oracle Billing, Batch/JIL, Integrations
Categories: Circular Dependency, Data Ownership, API Coverage, Batch Risk, Security, Compliance, Performance, Data Quality
Score 0-10 per cell, overall_risk_score 0-100."""


def build_prompt(assets, discovery):
    blocks = [f"=== {a.filename} ===\n{a.raw_summary}\n" for a in assets]
    disc = f"\nDISCOVERY: {discovery.summary}" if discovery else ""
    return f"Produce risk assessment JSON for this telco environment.\n\n{''.join(blocks)}{disc}\n\nReturn ONLY JSON."


async def run_risk_agent(assets, discovery):
    prompt = build_prompt(assets, discovery)
    print(f"[risk] Starting Claude API call")
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = response.content[0].text
        print(f"[risk] Got response, length={len(full_response)}")
        yield {"type": "chunk", "text": full_response}
    except Exception as e:
        print(f"[risk] Claude API error: {e}")
        yield {"type": "error", "message": f"Claude API error: {e}"}
        return

    try:
        clean = full_response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)
        data = json.loads(clean)
        risk_items = [RiskItem(**r) for r in data.get("risk_items", [])]
        result = RiskOutput(
            risk_items=risk_items,
            heatmap=data.get("heatmap", []),
            overall_risk_score=data.get("overall_risk_score", 0),
            summary=data.get("summary", "")
        )
        yield {"type": "result", "data": result.model_dump()}
    except Exception as e:
        print(f"[risk] Parse error: {e}")
        yield {"type": "error", "message": f"Parse error: {e}"}
