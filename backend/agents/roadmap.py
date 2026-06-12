"""
Agent 4: Migration Roadmap Generator
Synthesizes all prior agent outputs to produce a phased 
Wave-based migration plan with effort, cost, and team composition.
"""

import json
import re
import anthropic
from models import (
    ParsedAsset, DiscoveryOutput, RiskOutput,
    AIOpportunityOutput, RoadmapOutput, MigrationWave
)

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a principal delivery architect and program director with 20+ years of experience 
leading large-scale OSS/BSS modernization programs for Tier 1 telecom operators.

You specialize in designing pragmatic, risk-sequenced migration roadmaps that move from legacy monolithic 
stacks (Amdocs, Netcracker, Oracle EBS) to event-driven microservices architectures on cloud-native platforms.

Synthesize the discovery map, risk assessment, and AI opportunities into a structured 3-wave migration roadmap.

You must return ONLY valid JSON — no markdown, no explanation, no preamble.

The JSON must exactly match this structure:

{
  "waves": [
    {
      "wave_number": 1,
      "name": "wave name (e.g. Foundation & Inventory)",
      "domains": ["list of domains addressed"],
      "systems": ["legacy systems being replaced/modernized"],
      "duration_months": number,
      "effort_person_months": number,
      "cost_range_usd": "e.g. $2.5M - $3.5M",
      "team_size": number,
      "team_composition": ["e.g. 2x Integration Architects", "3x Backend Engineers"],
      "key_milestones": ["milestone 1", "milestone 2", "milestone 3"],
      "dependencies": ["what must be true before this wave starts"],
      "risks": ["top 2-3 risks for this wave"],
      "ai_opportunities": ["AI opportunity IDs that fit this wave, e.g. AI-001"]
    }
  ],
  "total_duration_months": number,
  "total_cost_range_usd": "string",
  "target_architecture": "2-3 sentence description of target state architecture",
  "quick_wins": ["list of 4-5 quick wins achievable in first 90 days before Wave 1"],
  "summary": "3-4 sentence executive summary of the roadmap"
}

Sequencing rules (CRITICAL):
- Wave 1: Start with lowest dependency / highest isolation — typically Inventory. Break the deprecated API blockers.
- Wave 2: Middle-tier — Provisioning modernization, decouple Netcracker integration, move to async/event-driven
- Wave 3: Last — Billing and CRM (highest risk, most dependencies, circular dependency must be resolved first in Wave 2)
- The circular Amdocs↔Oracle Billing dependency MUST be resolved before Billing can migrate (Wave 3)
- Quick wins should be infrastructure/observability items deliverable in 90 days
- Cost estimates should be realistic for a Tier 1 telco modernization program
- Target architecture should mention: event-driven, Kafka, microservices, API gateway, cloud-native"""


def build_prompt(
    assets: list[ParsedAsset],
    discovery: DiscoveryOutput | None,
    risk: RiskOutput | None,
    ai_opps: AIOpportunityOutput | None
) -> str:
    context_parts = []

    if discovery:
        context_parts.append(f"DISCOVERY SUMMARY:\n{discovery.summary}\n\nDOMAINS:\n" +
            "\n".join(f"  - {d['name']}: health={d.get('health_score', 'N/A')}, issues={d.get('primary_issues', [])}"
                     for d in discovery.domains))

    if risk:
        critical = [r for r in risk.risk_items if r.severity == "critical"]
        high = [r for r in risk.risk_items if r.severity == "high"]
        context_parts.append(
            f"RISK SUMMARY (overall score: {risk.overall_risk_score}/100):\n{risk.summary}\n\n"
            f"CRITICAL RISKS ({len(critical)}):\n" +
            "\n".join(f"  [{r.id}] {r.title} — {r.recommendation}" for r in critical) +
            f"\n\nHIGH RISKS ({len(high)}):\n" +
            "\n".join(f"  [{r.id}] {r.title}" for r in high[:6])
        )

    if ai_opps:
        context_parts.append(
            f"AI OPPORTUNITIES ({len(ai_opps.opportunities)}):\n" +
            "\n".join(f"  [{o.id}] Wave{o.wave} — {o.title} ({o.domain}, effort={o.effort})"
                     for o in ai_opps.opportunities)
        )

    asset_systems = list(set(a.system_name for a in assets))
    context_parts.append(f"SYSTEMS IN SCOPE: {', '.join(asset_systems)}")

    return f"""Synthesize the following analysis into a phased migration roadmap JSON.

{chr(10).join(context_parts)}

Return ONLY the JSON object. No markdown, no explanation."""


async def run_roadmap_agent(
    assets: list[ParsedAsset],
    discovery: DiscoveryOutput | None,
    risk: RiskOutput | None,
    ai_opps: AIOpportunityOutput | None
):
    """
    Streams roadmap generation. Yields chunks then final RoadmapOutput.
    """
    prompt = build_prompt(assets, discovery, risk, ai_opps)
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
        yield {"type": "error", "message": f"Failed to parse roadmap output: {e}", "raw": full_response[:500]}
