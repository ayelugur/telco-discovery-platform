import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, AIOpportunityOutput, RoadmapOutput, MigrationWave

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a principal delivery architect with 20+ years leading OSS/BSS modernization for Tier 1 telcos.

Return ONLY valid JSON:
{
  "waves": [{"wave_number": 1, "name": "name", "domains": ["list"], "systems": ["list"], "duration_months": 6, "effort_person_months": 24, "cost_range_usd": "$2M-$3M", "team_size": 8, "team_composition": ["2x Architects"], "key_milestones": ["milestone"], "dependencies": ["dep"], "risks": ["risk"], "ai_opportunities": ["AI-001"]}],
  "total_duration_months": 18,
  "total_cost_range_usd": "$8M-$12M",
  "target_architecture": "description mentioning Kafka, microservices, API gateway, cloud-native",
  "quick_wins": ["4-5 items in 90 days"],
  "summary": "3-4 sentences"
}

Wave sequencing: Wave 1=Inventory (lowest deps), Wave 2=Provisioning (decouple Netcracker), Wave 3=Billing+CRM (highest risk, last)."""


def build_prompt(assets, discovery, risk, ai_opps):
    ctx = []
    if discovery:
        ctx.append(f"DISCOVERY: {discovery.summary}")
    if risk:
        critical = [r for r in risk.risk_items if r.severity == "critical"]
        ctx.append(f"RISK SCORE: {risk.overall_risk_score}/100")
        ctx.append("CRITICAL: " + "; ".join(f"{r.title}" for r in critical[:4]))
    if ai_opps:
        ctx.append("AI OPPS: " + ", ".join(f"{o.id} Wave{o.wave} {o.title}" for o in ai_opps.opportunities[:8]))
    return f"Generate migration roadmap JSON.\n\n{chr(10).join(ctx)}\n\nReturn ONLY JSON."


async def run_roadmap_agent(assets, discovery, risk, ai_opps):
    prompt = build_prompt(assets, discovery, risk, ai_opps)
    print(f"[roadmap] Starting Claude API call")
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = response.content[0].text
        print(f"[roadmap] Got response, length={len(full_response)}")
        yield {"type": "chunk", "text": full_response}
    except Exception as e:
        print(f"[roadmap] Claude API error: {e}")
        yield {"type": "error", "message": f"Claude API error: {e}"}
        return

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
        print(f"[roadmap] Parse error: {e}")
        yield {"type": "error", "message": f"Parse error: {e}"}
