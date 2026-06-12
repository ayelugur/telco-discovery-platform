"""
Agent 2: Risk & Architecture Analyzer
Detects architectural flaws, security findings, compliance risks,
and generates the risk heatmap data.
"""

import json
import re
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, RiskItem

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a principal architect and security consultant specializing in legacy telecom modernization risk assessment.
You have deep expertise in OSS/BSS architecture, PCI-DSS, GDPR, and enterprise integration patterns.

Analyze the provided technical assets and discovery map to identify ALL architectural risks, security findings, 
compliance issues, and operational hazards.

You must return ONLY valid JSON — no markdown, no explanation, no preamble.

The JSON must exactly match this structure:

{
  "risk_items": [
    {
      "id": "RISK-001",
      "system": "system name",
      "category": "Circular Dependency | Data Ownership | API Coverage | Batch Risk | Security | Compliance | Performance | Data Quality",
      "title": "short risk title",
      "description": "detailed description with specific evidence from the assets (table names, proc names, ticket IDs)",
      "severity": "low | medium | high | critical",
      "impact": "business impact if not addressed",
      "recommendation": "specific remediation recommendation"
    }
  ],
  "heatmap": [
    {
      "system": "system name",
      "category": "risk category",
      "score": 0-10,
      "label": "short label for cell",
      "risk_ids": ["RISK-001"]
    }
  ],
  "overall_risk_score": 0-100,
  "summary": "3-4 sentence executive summary of risk posture"
}

Heatmap systems must be: ["Amdocs CRM", "Netcracker", "Oracle Billing", "Batch/JIL", "Integrations"]
Heatmap categories must be: ["Circular Dependency", "Data Ownership", "API Coverage", "Batch Risk", "Security", "Compliance", "Performance", "Data Quality"]

Rules:
- Be specific — cite actual ticket IDs, table names, procedure names, column names from the assets
- Score 0=no risk, 10=critical/immediate risk
- Every open security/compliance finding from tickets must become a risk item
- The circular dependency between Amdocs and Oracle Billing is a critical finding
- Recurring incidents indicate systemic architectural risk
- Identify risks that BLOCK modernization (e.g. deprecated endpoint that can't be retired)"""


def build_prompt(assets: list[ParsedAsset], discovery: DiscoveryOutput | None) -> str:
    asset_blocks = []
    for asset in assets:
        asset_blocks.append(f"=== {asset.filename} ({asset.asset_type}) ===\n{asset.raw_summary}\n")

    discovery_block = ""
    if discovery:
        discovery_block = f"""
=== DISCOVERY MAP SUMMARY ===
{discovery.summary}

Edges identified: {len(discovery.edges)}
High-risk edges: {[e.label for e in discovery.edges if e.risk in ('high', 'critical')]}
"""

    return f"""Analyze these technical assets and the discovery map to produce a comprehensive risk assessment JSON.

{"".join(asset_blocks)}

{discovery_block}

Return ONLY the JSON object. No markdown, no explanation."""


async def run_risk_agent(assets: list[ParsedAsset], discovery: DiscoveryOutput | None):
    """
    Streams risk analysis. Yields text chunks then final RiskOutput.
    """
    prompt = build_prompt(assets, discovery)
    full_response = ""

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4000,
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
