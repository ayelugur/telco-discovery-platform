import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, RiskItem

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a principal architect and security consultant specializing in legacy telecom modernization risk assessment.
You have deep expertise in OSS/BSS architecture, PCI-DSS, GDPR, and enterprise integration patterns.

You must return ONLY valid JSON — no markdown, no explanation, no preamble.

{
  "risk_items": [
    {
      "id": "RISK-001",
      "system": "system name",
      "category": "Circular Dependency | Data Ownership | API Coverage | Batch Risk | Security | Compliance | Performance | Data Quality",
      "title": "short risk title",
      "description": "detailed description with specific evidence from the assets",
      "severity": "low | medium | high | critical",
      "impact": "business impact if not addressed",
      "recommendation": "specific remediation recommendation"
    }
  ],
  "heatmap": [
    {
      "system": "system name",
      "category": "risk category",
      "score": 0,
      "label": "short label",
      "risk_ids": ["RISK-001"]
    }
  ],
  "overall_risk_score": 0,
  "summary": "3-4 sentence executive summary"
}

Heatmap systems: ["Amdocs CRM", "Netcracker", "Oracle Billing", "Batch/JIL", "Integrations"]
Heatmap categories: ["Circular Dependency", "Data Ownership", "API Coverage", "Batch Risk", "Security", "Compliance", "Performance", "Data Quality"]
Score: 0=no risk, 10=critical. overall_risk_score: 0-100."""


def build_prompt(assets, discovery):
    blocks = [f"=== {a.filename} ({a.asset_type}) ===\n{a.raw_summary}\n" for a in assets]
    discovery_block = f"\nDISCOVERY SUMMARY:\n{discovery.summary}\n" if discovery else ""
    return f"""Analyze these assets and produce a comprehensive risk assessment JSON.

{"".join(blocks)}{discovery_block}

Return ONLY the JSON object. No markdown, no explanation."""


async def run_risk_agent(assets: list[ParsedAsset], discovery: DiscoveryOutput | None):
    prompt = build_prompt(assets, discovery)
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
        risk_items = [RiskItem(**r) for r in data.get("risk_items", [])]
        result = RiskOutput(
            risk_items=risk_items,
            heatmap=data.get("heatmap", []),
            overall_risk_score=data.get("overall_risk_score", 0),
            summary=data.get("summary", "")
        )
        yield {"type": "result", "data": result.model_dump()}
    except Exception as e:
        yield {"type": "error", "message": f"Failed to parse risk output: {e}", "raw": full_response[:500]}
