import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, GraphNode, GraphEdge

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a senior enterprise architect specializing in legacy telecom system modernization. 
You have deep expertise in OSS/BSS stacks including Amdocs, Netcracker, Oracle EBS, HP TeMIP, and Remedy.

Analyze raw technical assets from a legacy telecom operator and produce a precise dependency map.

Return ONLY valid JSON matching this structure exactly:
{
  "nodes": [{"id": "snake_case_id", "label": "Human Name", "type": "system|domain|database|api|batch_job", "domain": "CRM|Billing|Provisioning|Inventory|Assurance|Integration", "status": "healthy|at_risk|critical", "metadata": {}}],
  "edges": [{"from_id": "id", "to_id": "id", "label": "what flows", "type": "sync_rest|sync_soap|db_link|batch_file|event|async_rest", "risk": "low|medium|high|critical"}],
  "domains": [{"name": "string", "systems": ["list"], "entity_count": 0, "api_surface": 0, "health_score": 0, "primary_issues": ["list"]}],
  "summary": "3-4 sentence executive summary"
}

Rules: every integration = edge, circular deps = critical risk, DB links = high risk, use actual names from assets."""


def build_prompt(assets):
    blocks = [f"=== {a.filename} ({a.asset_type}) ===\n{a.raw_summary}\n" for a in assets]
    return f"Analyze these {len(assets)} telco assets and return discovery graph JSON.\n\n{''.join(blocks)}\n\nReturn ONLY JSON."


async def run_discovery_agent(assets: list[ParsedAsset]):
    prompt = build_prompt(assets)
    full_response = ""

    print(f"[discovery] Starting Claude API call, prompt length={len(prompt)}")

    try:
        # Use non-streaming first to confirm API works, then we'll add streaming back
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = response.content[0].text
        print(f"[discovery] Got response, length={len(full_response)}")

        # Yield the full text as one chunk so the UI shows output
        yield {"type": "chunk", "text": full_response}

    except Exception as e:
        print(f"[discovery] Claude API error: {e}")
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
        print(f"[discovery] Parse error: {e}\nRaw: {full_response[:300]}")
        yield {"type": "error", "message": f"Parse error: {e}"}
