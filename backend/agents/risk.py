import re
import json
import anthropic
from models import ParsedAsset, DiscoveryOutput, RiskOutput, RiskItem

client = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are a telecom modernization risk assessor.

Return ONLY compact JSON — no whitespace, no newlines, no markdown.

{"risk_items":[{"id":"RISK-001","system":"Amdocs CRM","category":"Circular Dependency","title":"CRM-Billing deadlock risk","description":"SP_SUBMIT_ORDER calls Oracle Billing PKG_BILLING.VALIDATE_PRODUCT which calls back to Amdocs CUSTOMER_MASTER creating circular sync dependency. Caused INC-2023-0445 deadlock.","severity":"critical","impact":"Order submission outage under load","recommendation":"Break circular dependency with async event queue"}],"heatmap":[{"system":"Amdocs CRM","category":"Circular Dependency","score":9,"label":"Deadlock risk","risk_ids":["RISK-001"]}],"overall_risk_score":72,"summary":"Two sentence summary."}

Systems (use exactly): Amdocs CRM, Netcracker, Oracle Billing, Batch/JIL, Integrations
Categories (use exactly): Circular Dependency, Data Ownership, API Coverage, Batch Risk, Security, Compliance, Performance, Data Quality
Scores: 0-10 per heatmap cell. overall_risk_score: 0-100.
Limits: 10-12 risk items max, one heatmap entry per system+category combo that has risk > 0.
Compact JSON only — no pretty printing."""


def build_prompt(assets, discovery):
    blocks = []
    for a in assets:
        summary = a.raw_summary[:600] + ('...' if len(a.raw_summary) > 600 else '')
        blocks.append(f"[{a.system_name}]\n{summary}")
    disc = f"\nDISCOVERY SUMMARY: {discovery.summary}" if discovery else ""
    return f"Assess risks in this telco environment. Return compact JSON only.\n\n" + "\n\n".join(blocks) + disc


async def run_risk_agent(assets, discovery):
    prompt = build_prompt(assets, discovery)
    print(f"[risk] prompt={len(prompt)} chars")
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        full_response = response.content[0].text
        print(f"[risk] response={len(full_response)} chars")
        yield {"type": "chunk", "text": "Identifying architectural risks and compliance findings..."}
    except Exception as e:
        print(f"[risk] API error: {e}")
        yield {"type": "error", "message": f"Claude API error: {e}"}
        return

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
        print(f"[risk] parse error: {e}\nraw[:300]: {full_response[:300]}")
        yield {"type": "error", "message": f"Parse error: {e}"}
