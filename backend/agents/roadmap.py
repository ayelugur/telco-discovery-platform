import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, AIOpportunityOutput, RoadmapOutput, MigrationWave

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a principal delivery architect with 20+ years leading OSS/BSS modernization programs for Tier 1 telcos.

You must return ONLY valid JSON — no markdown, no explanation, no preamble.

{
  "waves": [
    {
      "wave_number": 1,
      "name": "wave name",
      "domains": ["domains addressed"],
      "systems": ["legacy systems"],
      "duration_months": 6,
      "effort_person_months": 24,
      "cost_range_usd": "$2M - $3M",
      "team_size": 8,
      "team_composition": ["2x Integration Architects", "3x Backend Engineers"],
      "key_milestones": ["milestone 1", "milestone 2"],
      "dependencies": ["what must be true first"],
      "risks": ["top 2-3 risks"],
      "ai_opportunities": ["AI-001"]
    }
  ],
  "total_duration_months": 18,
  "total_cost_range_usd": "$8M - $12M",
  "target_architecture": "description of target state",
  "quick_wins": ["4-5 items achievable in 90 days"],
  "summary": "3-4 sentence executive summary"
}

Sequencing rules:
- Wave 1: lowest dependency — typically Inventory
- Wave 2: Provisioning, decouple Netcracker, move to async/event-driven
- Wave 3: Billing and CRM last — circular dependency must be resolved first
- Target architecture must mention: Kafka, microservices, API gateway, cloud-native"""


def build_prompt(assets, discovery, risk, ai_opps):
    ctx = []
    if discovery:
        ctx.append(f"DISCOVERY: {discovery.summary}")
        ctx.append("DOMAINS: " + ", ".join(f"{d['name']} (health={d.get('health_score','?')})" for d in discovery.domains))
    if risk:
        critical = [r for r in risk.risk_items if r.severity == "critical"]
        ctx.append(f"RISK SCORE: {risk.overall_risk_score}/100. CRITICAL RISKS: " +
                   "; ".join(f"{r.title} → {r.recommendation}" for r in critical[:4]))
    if ai_opps:
        ctx.append("AI OPPS: " + ", ".join(f"{o.id} Wave{o.wave} {o.title}" for o in ai_opps.opportunities))

    return f"""Synthesize this analysis into a phased migration roadmap.

{chr(10).join(ctx)}

Return ONLY the JSON object. No markdown, no explanation."""


async def run_roadmap_agent(assets, discovery, risk, ai_opps):
    prompt = build_prompt(assets, discovery, risk, ai_opps)
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
        waves = [MigrationWave(**w) for w in data.get("waves", [])]
        result = RoadmapOutput(
            waves=waves,
            total_duration_months=data.get("total_duration_months", 0),
            total_cost_range_usd=data.get("total_cost_range_usd", ""),
            target_architecture=data.get("target_architecture", ""),
            quick_wins=data.get("quick_wins", []),
            summary=data.get("summary", "")
        )
        yield {"type": "result", "data": result.model_dump()}
    except Exception as e:
        yield {"type": "error", "message": f"Failed to parse roadmap: {e}", "raw": full_response[:500]}
