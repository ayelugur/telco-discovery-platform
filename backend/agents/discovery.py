import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, GraphNode, GraphEdge

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a senior enterprise architect analyzing legacy telecom systems.

Return ONLY a compact JSON object — no whitespace, no newlines, no markdown.

{"nodes":[{"id":"amdocs_crm","label":"Amdocs CRM","type":"system","domain":"CRM","status":"at_risk","metadata":{}}],"edges":[{"from_id":"amdocs_crm","to_id":"oracle_billing","label":"DB Link sync","type":"db_link","risk":"critical"}],"domains":[{"name":"CRM","systems":["Amdocs CRM"],"entity_count":5,"api_surface":3,"health_score":45,"primary_issues":["Circular dependency with Billing","No caching"]}],"summary":"Brief 2-sentence summary."}

Rules:
- 8-12 nodes maximum, 10-15 edges maximum, 5 domains maximum
- Every cross-system integration = one edge
- Circular Amdocs↔Oracle dependency = critical edge
- DB links = high/critical risk
- Compact JSON only — no pretty printing"""


def build_prompt(assets):
    # Send condensed summaries only to keep prompt short
    blocks = []
    for a in assets:
        # Truncate each asset summary to 800 chars
        summary = a.raw_summary[:800] + ('...' if len(a.raw_summary) > 800 else '')
        blocks.append(f"[{a.system_name} / {a.asset_type}]\n{summary}")
    return f"Analyze these {len(assets)} telco assets. Return compact JSON only.\n\n" + "\n\n".join(blocks)


async def run_discovery_agent(assets: list[ParsedAsset]):
    prompt = build_prompt(assets)
    print(f"[discovery] prompt={len(prompt)} chars")
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = response.content[0].text
        print(f"[discovery] response={len(full_response)} chars")
        yield {"type": "chunk", "text": "Mapping system dependencies and functional domains..."}
    except Exception as e:
        print(f"[discovery] API error: {e}")
        yield {"type": "error", "message": f"Claude API error: {e}"}
        return

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
        print(f"[discovery] parse error: {e}\nraw[:300]: {full_response[:300]}")
        yield {"type": "error", "message": f"Parse error: {e}"}
