from pydantic import BaseModel
from typing import Optional, Any


# ── Parsed Asset ─────────────────────────────────────────────────────────────

class ParsedAsset(BaseModel):
    filename: str
    asset_type: str          # swagger | sql_schema | json_schema | ticket_log | jil_schedule
    system_name: str
    raw_summary: str         # Condensed text fed to agents
    metadata: dict[str, Any] = {}


# ── Agent Outputs ─────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    type: str                # system | domain | database | api | batch_job
    domain: Optional[str]    # CRM | Billing | Provisioning | Inventory | Assurance
    status: Optional[str]    # healthy | at_risk | critical
    metadata: dict[str, Any] = {}


class GraphEdge(BaseModel):
    from_id: str
    to_id: str
    label: str
    type: str                # sync_rest | sync_soap | db_link | batch_file | event | async_rest
    risk: Optional[str]      # low | medium | high | critical


class DiscoveryOutput(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    domains: list[dict[str, Any]]   # Domain summary cards
    summary: str


class RiskItem(BaseModel):
    id: str
    system: str
    category: str            # Data Ownership | Circular Dependency | API Coverage | Batch Risk | Security | Compliance
    title: str
    description: str
    severity: str            # low | medium | high | critical
    impact: str
    recommendation: str


class RiskOutput(BaseModel):
    risk_items: list[RiskItem]
    heatmap: list[dict[str, Any]]   # [{system, category, score, label}]
    overall_risk_score: int          # 0-100
    summary: str


class AIOpportunity(BaseModel):
    id: str
    title: str
    domain: str
    opportunity_type: str    # automation | prediction | nlp | anomaly_detection | optimization
    description: str
    business_value: str
    effort: str              # low | medium | high
    wave: int                # Which migration wave it fits


class AIOpportunityOutput(BaseModel):
    opportunities: list[AIOpportunity]
    summary: str


class MigrationWave(BaseModel):
    wave_number: int
    name: str
    domains: list[str]
    systems: list[str]
    duration_months: int
    effort_person_months: int
    cost_range_usd: str
    team_size: int
    team_composition: list[str]
    key_milestones: list[str]
    dependencies: list[str]
    risks: list[str]
    ai_opportunities: list[str]


class RoadmapOutput(BaseModel):
    waves: list[MigrationWave]
    total_duration_months: int
    total_cost_range_usd: str
    target_architecture: str
    quick_wins: list[str]
    summary: str


# ── API Request/Response ──────────────────────────────────────────────────────

class AnalysisState(BaseModel):
    assets: list[ParsedAsset] = []
    discovery: Optional[DiscoveryOutput] = None
    risk: Optional[RiskOutput] = None
    ai_opportunities: Optional[AIOpportunityOutput] = None
    roadmap: Optional[RoadmapOutput] = None
