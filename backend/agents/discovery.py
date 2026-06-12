"""
Agent 1: Discovery & Dependency Mapper
Identifies functional domains, maps data lineage, 
and surfaces runtime dependencies across all ingested assets.
"""

import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, GraphNode, GraphEdge

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a senior enterprise architect specializing in legacy telecom system modernization. 
You have deep expertise in OSS/BSS stacks including Amdocs, Netcracker, Oracle EBS, HP TeMIP, and Remedy.

Your task is to analyze raw technical assets from a legacy telecom operator and produce a precise 
dependency map and functional domain classification.

You must return ONLY valid JSON — no markdown, no explanation, no preamble.
The JSON must exactly match this structure:

{
  "nodes": [
    {
      "id": "string (snake_case unique identifier)",
      "label": "string (human readable name)",
      "type": "system | domain | database | api | batch_job",
      "domain": "CRM | Billing | Provisioning | Inventory | Assurance | Integration",
      "status": "healthy | at_risk | critical",
      "metadata": {}
    }
  ],
  "edges": [
    {
      "from_id": "string",
      "to_id": "string", 
      "label": "string (what data/call flows)",
      "type": "sync_rest | sync_soap | db_link | batch_file | event | async_rest",
      "risk": "low | medium | high | critical"
    }
  ],
  "domains": [
    {
      "name": "string",
      "systems": ["list of system names"],
      "entity_count": number,
      "api_surface": number,
      "health_score": number (0-100),
      "primary_issues": ["list of key issues"]
    }
  ],
  "summary": "string (3-4 sentence executive summary of what was discovered)"
}

Rules:
- Every integration mentioned in the assets must become an edge
- Circular dependencies must be included and marked risk=critical
- Deprecated API paths that are still consumed must be included
- DB links are high-risk edges by default
- Be specific — use actual table names, procedure names, endpoint paths from the assets
- Domain health_score should reflect actual issues found: 0=broken, 100=perfect"""


def build_prompt(assets: list[ParsedAsset]) -> str:
    asset_blocks = []
    for asset in assets:
        asset_blocks.append(
            f"=== ASSET: {asset.filename} ({asset.asset_type}) ===\n{asset.raw_summary}\n"
        )
    combined = "\n\n".join(asset_blocks)
    return f"""Analyze these {len(assets)} technical assets from a legacy telecom operator and produce the discovery graph JSON.

{combined}

Remember: return ONLY the JSON object. No markdown fences, no explanation."""


async def run_discovery_agent(assets: list[ParsedAsset]):
    """
    Streams the discovery analysis. Yields text chunks, then yields
    the final parsed DiscoveryOutput as the last item.
    """
    prompt = build_prompt(assets)

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

    # Parse the JSON output
    try:
        # Strip markdown fences if model added them anyway
        clean = full_response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)
        
        data = json.loads(clean)
        
        nodes = [GraphNode(**n) for n in data.get("nodes", [])]
        edges = [GraphEdge(**e) for e in data.get("edges", [])]
        
        result = DiscoveryOutput(
            nodes=nodes,
            edges=edges,
            domains=data.get("domains", []),
            summary=data.get("summary", "")
        )
        yield {"type": "result", "data": result.model_dump()}
    except Exception as e:
        yield {"type": "error", "message": f"Failed to parse discovery output: {e}", "raw": full_response[:500]}


import re
