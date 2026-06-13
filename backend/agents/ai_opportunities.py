import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, AIOpportunityOutput, AIOpportunity

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a telecom AI transformation strategist.

Return ONLY compact JSON — no whitespace, no newlines, no markdown.

{"opportunities":[{"id":"AI-001","title":"Churn Prediction Refresh","domain":"CRM","opportunity_type":"prediction","description":"CUSTOMER_SEGMENT.CHURN_RISK_SCORE refreshed weekly from stale Teradata model with no feedback loop. Replace with real-time ML model trained on actual churn events.","business_value":"Reduce churn 15-20% through timely intervention","effort":"medium","wave":1}],"summary":"Two sentence summary."}

Limits: 8 opportunities maximum. Keep descriptions under 150 chars.
Domains: CRM, Billing, Provisioning, Inventory, Assurance, Cross-Domain
Types: automation, prediction, nlp, anomaly_detection, optimization, generative_ai
Wave: 1=quick win, 2=mid, 3=post-migration
Compact JSON only — no pretty printing."""


def build_prompt(assets, discovery, risk):
    blocks = []
    for a in assets:
        summary = a.raw_summary[:500] + ('...' if len(a.raw_summary) > 500 else '')
        blocks.append(f"[{a.system_name}]\n{summary}")
    ctx = ""
    if discovery: ctx += f"\nDISCOVERY: {discovery.summary}"
    if risk: ctx += f"\nTOP RISKS: {', '.join(r.title for r in risk.risk_items[:4])}"
    return "Find AI/ML opportunities in this telco environment. Return compact JSON only.\n\n" + "\n\n".join(blocks) + ctx


async def run_ai_opportunities_agent(assets, discovery, risk):
    prompt = build_prompt(assets, discovery, risk)
    print(f"[ai_opps] prompt={len(prompt)} chars")
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = response.content[0].text
        print(f"[ai_opps] response={len(full_response)} chars")
        yield {"type": "chunk", "text": "Scanning for AI and automation opportunities..."}
    except Exception as e:
        print(f"[ai_opps] API error: {e}")
        yield {"type": "error", "message": f"Claude API error: {e}"}
        return

    try:
        clean = full_response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)
        data = json.loads(clean)
        opps = [AIOpportunity(**o) for o in data.get("opportunities", [])]
        result = AIOpportunityOutput(opportunities=opps, summary=data.get("summary", ""))
        yield {"type": "result", "data": result.model_dump()}
    except Exception as e:
        print(f"[ai_opps] parse error: {e}\nraw[:300]: {full_response[:300]}")
        yield {"type": "error", "message": f"Parse error: {e}"}
