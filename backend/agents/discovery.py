import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, GraphNode, GraphEdge

client = anthropic.AsyncAnthropic()

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
      "entity_count": 0,
      "api_surface": 0,
      "health_score": 0,
      "primary_issues": ["list of key issues"]
    }
  ],
  "summary": "string (3-4 sentence executive summary)"
}

Rules:
- Every integration mentioned must become an edge
- Circular dependencies must be marked risk=critical
- Deprecated API paths still consumed must be included
- DB links are high-risk edges by default
- Use actual table names, procedure names, endpoint paths from the assets
- Domain health_score: 0=broken, 100=perfect"""


def build_prompt(assets: list[ParsedAsset]) -> str:
    blocks = [f"=== ASSET: {a.filename} ({a.asset_type}) ===\n{a.raw_summary}\n" for a in assets]
    return f"""Analyze these {len(assets)} technical assets from a legacy telecom operator and produce the discovery graph JSON.

{"".join(blocks)}

Return ONLY the JSON object. No markdown fences, no explanation."""


async def run_discovery_agent(assets: list[ParsedAsset]):
    prompt = build_prompt(assets)
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
        nodes = [GraphNode(**n) for n in data.get("nodes", [])]
        edges = [GraphEdge(**e) for e in data.get("edges", [])]
        result = DiscoveryOutput(
            nodes=nodes, edges=edges,
            domains=data.get("domains", []),
            summary=data.get("summary", "")
        )
        yield {"type": "result", "data": result.model_dump()}
    except Exception as e:
        yield {"type": "error", "message": f"Failed to parse discovery output: {e}", "raw": full_response[:500]}
