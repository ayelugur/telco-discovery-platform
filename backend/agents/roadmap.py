import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, AIOpportunityOutput, RoadmapOutput, MigrationWave

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a principal delivery architect for OSS/BSS modernization programs.

Return ONLY compact JSON — no whitespace, no newlines, no markdown.

{"waves":[{"wave_number":1,"name":"Foundation & Inventory","domains":["Inventory"],"systems":["Netcracker Inventory"],"duration_months":6,"effort_person_months":24,"cost_range_usd":"$2M-$3M","team_size":8,"team_composition":["2x Integration Architects","3x Backend Engineers","2x QA","1x PM"],"key_milestones":["API gateway live","Inventory microservice deployed","Legacy decommissioned"],"dependencies":["Cloud infrastructure provisioned"],"risks":["Data migration complexity"],"ai_opportunities":["AI-001"]}],"total_duration_months":18,"total_cost_range_usd":"$8M-$12M","target_architecture":"Event-driven microservices on cloud-native platform using Kafka for async integration, replacing synchronous DB links and SOAP calls.","quick_wins":["Deploy API gateway","Add Redis caching for Customer360","Implement circuit breaker on Netcracker SOAP calls"],"summary":"Two sentence summary."}

Rules:
- Exactly 3 waves
- Wave 1=Inventory (lowest deps), Wave 2=Provisioning, Wave 3=Billing+CRM (highest risk)
- Keep milestones to 3 per wave, team_composition to 4 roles max
- Compact JSON only — no pretty printing"""


def build_prompt(assets, discovery, risk, ai_opps):
    ctx = []
    if discovery:
        ctx.append(f"DOMAINS: {', '.join(d['name'] + '(health=' + str(d.get('health_score','?')) + ')' for d in discovery.domains)}")
        ctx.append(f"DISCOVERY: {discovery.summary}")
    if risk:
        critical = [r for r in risk.risk_items if r.severity == "critical"]
        ctx.append(f"RISK SCORE: {risk.overall_risk_score}/100. CRITICAL: {'; '.join(r.title for r in critical[:3])}")
    if ai_opps:
        ctx.append("AI OPPS: " + ", ".join(f"{o.id} W{o.wave} {o.title}" for o in ai_opps.opportunities[:6]))
    return "Generate 3-wave migration roadmap. Return compact JSON only.\n\n" + "\n".join(ctx)


async def run_roadmap_agent(assets, discovery, risk, ai_opps):
    prompt = build_prompt(assets, discovery, risk, ai_opps)
    print(f"[roadmap] prompt={len(prompt)} chars")
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = response.content[0].text
        print(f"[roadmap] response={len(full_response)} chars")
        yield {"type": "chunk", "text": "Generating phased migration wave plan..."}
    except Exception as e:
        print(f"[roadmap] API error: {e}")
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
        print(f"[roadmap] parse error: {e}\nraw[:300]: {full_response[:300]}")
        yield {"type": "error", "message": f"Parse error: {e}"}
