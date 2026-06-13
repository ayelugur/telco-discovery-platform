"""
Asset parsers: convert raw uploaded/pre-loaded files into
condensed text summaries that agents can reason over.
"""

import json
import re
import yaml
import sqlparse
from pathlib import Path
from models import ParsedAsset


# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated, {len(text) - max_chars} chars omitted]"


# ── Swagger / OpenAPI Parser ──────────────────────────────────────────────────

def parse_swagger(filename: str, content: str) -> ParsedAsset:
    try:
        spec = yaml.safe_load(content) if content.strip().startswith(('openapi', 'swagger', 'info')) else json.loads(content)
    except Exception:
        spec = {}

    title = spec.get("info", {}).get("title", filename)
    version = spec.get("info", {}).get("version", "unknown")
    description = spec.get("info", {}).get("description", "")
    host = spec.get("host", spec.get("servers", [{}])[0].get("url", "unknown") if spec.get("servers") else "unknown")

    paths = spec.get("paths", {})
    endpoints = []
    deprecated_endpoints = []
    tags_seen = set()

    for path, methods in paths.items():
        for method, detail in methods.items():
            if not isinstance(detail, dict):
                continue
            tags = detail.get("tags", [])
            tags_seen.update(tags)
            summary = detail.get("summary", "")
            desc = detail.get("description", "")[:200]
            is_deprecated = "[DEPRECATED]" in summary or "DEPRECATED" in desc.upper()
            entry = f"  {method.upper()} {path} — {summary}"
            if is_deprecated:
                deprecated_endpoints.append(entry)
            else:
                endpoints.append(entry)

    consumers = []
    if "x-integration-consumers" in spec:
        for c in spec["x-integration-consumers"]:
            consumers.append(f"  - {c.get('system')}: {c.get('integration_type')} → {', '.join(c.get('endpoints', []))}")

    known_issues = []
    if "x-known-issues" in spec:
        for i in spec["x-known-issues"]:
            known_issues.append(f"  [{i.get('id')}] {i.get('description')}")

    lines = [
        f"SYSTEM: {title} (v{version})",
        f"HOST: {host}",
        f"API DOMAINS/TAGS: {', '.join(tags_seen)}",
        "",
        f"DESCRIPTION:\n{_truncate(description, 800)}",
        "",
        f"ACTIVE ENDPOINTS ({len(endpoints)}):",
        *endpoints[:30],
        "",
        f"DEPRECATED ENDPOINTS STILL IN USE ({len(deprecated_endpoints)}):",
        *deprecated_endpoints,
        "",
        "INTEGRATION CONSUMERS:",
        *(consumers or ["  Not documented"]),
        "",
        "KNOWN ISSUES:",
        *(known_issues or ["  None documented"]),
    ]

    system_name = title.split()[0] if title else filename
    return ParsedAsset(
        filename=filename,
        asset_type="swagger",
        system_name=system_name,
        raw_summary="\n".join(lines),
        metadata={"endpoint_count": len(endpoints), "deprecated_count": len(deprecated_endpoints), "tags": list(tags_seen)}
    )


# ── SQL Schema Parser ─────────────────────────────────────────────────────────

def parse_sql_schema(filename: str, content: str) -> ParsedAsset:
    tables = []
    current_table = None
    columns = []
    known_issues_block = []
    cross_system_notes = []
    stored_procs = []

    # Extract table names
    table_pattern = re.compile(r'CREATE\s+TABLE\s+(\S+)\s*\(', re.IGNORECASE)
    col_pattern = re.compile(r'^\s{2,4}(\w+)\s+([\w()]+).*?(?:--\s*(.+))?$')
    issue_pattern = re.compile(r'--\s*(KNOWN ISSUE|CRITICAL|RISK|SECURITY|WARNING|NOTE|TODO):\s*(.+)', re.IGNORECASE)
    proc_pattern = re.compile(r'(PKG_\w+\.\w+|SP_\w+)', re.IGNORECASE)

    # Pull table names
    found_tables = table_pattern.findall(content)

    # Pull inline comments with issues
    issues = []
    for line in content.splitlines():
        m = issue_pattern.search(line)
        if m:
            issues.append(f"  [{m.group(1).upper()}] {m.group(2).strip()}")

    # Pull stored proc references
    procs = list(set(proc_pattern.findall(content)))

    # Extract cross-system notes block
    cross_section = re.search(r'CROSS-SYSTEM INTEGRATION SUMMARY.*?(?=\*/)', content, re.DOTALL | re.IGNORECASE)
    cross_text = cross_section.group(0)[:1500] if cross_section else ""

    # Extract circular dependency callout
    circular = re.search(r'CIRCULAR DEPENDENCY.*?(?=\n\n|\*/)', content, re.DOTALL | re.IGNORECASE)
    circular_text = circular.group(0)[:600] if circular else ""

    # Detect data ownership conflicts
    ownership = re.search(r'DATA OWNERSHIP.*?(?=\n\n|\*/)', content, re.DOTALL | re.IGNORECASE)
    ownership_text = ownership.group(0)[:600] if ownership else ""

    # Approximate row counts
    row_counts = re.findall(r'row_count_approx.*?(\d[\d,]+)', content)

    lines = [
        f"SYSTEM: Oracle Billing Database (custom TELCO_BILLING schema)",
        f"FILE: {filename}",
        "",
        f"TABLES FOUND ({len(found_tables)}): {', '.join(found_tables)}",
        "",
        f"STORED PROCEDURES / PACKAGES REFERENCED: {', '.join(procs[:20])}",
        "",
        "INLINE ISSUES, RISKS & WARNINGS:",
        *issues[:40],
        "",
        "CROSS-SYSTEM INTEGRATION:",
        cross_text,
        "",
        "CIRCULAR DEPENDENCY ANALYSIS:",
        circular_text,
        "",
        "DATA OWNERSHIP CONFLICTS:",
        ownership_text,
    ]

    system_name = "Oracle Billing"
    return ParsedAsset(
        filename=filename,
        asset_type="sql_schema",
        system_name=system_name,
        raw_summary=_truncate("\n".join(lines), 7000),
        metadata={"table_count": len(found_tables), "tables": found_tables, "issue_count": len(issues)}
    )


# ── JSON Schema Parser (Amdocs CRM) ──────────────────────────────────────────

def parse_json_schema(filename: str, content: str) -> ParsedAsset:
    try:
        data = json.loads(content)
    except Exception:
        return ParsedAsset(filename=filename, asset_type="json_schema",
                           system_name=filename, raw_summary=content[:3000])

    system = data.get("system", filename)
    vendor = data.get("vendor", "Unknown")
    version = data.get("version", "Unknown")
    last_doc = data.get("last_documented", "Unknown")
    top_note = data.get("note", "")

    schemas = data.get("schemas", [])
    table_summaries = []
    all_issues = []
    all_procs = []
    all_db_links = []
    all_interfaces = []

    for schema in schemas:
        schema_name = schema.get("schema_name", "")
        for table in schema.get("tables", []):
            tname = table.get("table_name", "")
            rows = table.get("row_count_approx", "unknown")
            desc = table.get("description", "")[:150]
            cols = [c["name"] for c in table.get("columns", [])]
            issues = table.get("known_issues", [])
            table_summaries.append(f"  {schema_name}.{tname} (~{rows:,} rows): {desc}")
            for issue in issues:
                all_issues.append(f"  [{tname}] {issue}")

        for proc in schema.get("stored_procedures", []):
            pname = proc.get("name", "")
            pdesc = proc.get("description", "")
            pext = proc.get("calls_external", [])
            pissues = proc.get("known_issues", "")
            all_procs.append(f"  {pname}: {pdesc}")
            if pext:
                all_procs.append(f"    → Calls: {', '.join(pext) if isinstance(pext, list) else pext}")
            if pissues:
                all_procs.append(f"    ⚠ {pissues}")

        for link in schema.get("db_links", []):
            all_db_links.append(f"  {link.get('name')} → {link.get('target')}: {link.get('description')}")

    for iface in data.get("integration_interfaces", []):
        all_interfaces.append(
            f"  {iface.get('name')} [{iface.get('type')}] {iface.get('direction', '')} — {iface.get('notes', '')}"
        )

    lines = [
        f"SYSTEM: {system} (vendor: {vendor}, version: {version})",
        f"LAST DOCUMENTED: {last_doc}",
        f"NOTE: {top_note}",
        "",
        f"TABLES ({len(table_summaries)}):",
        *table_summaries,
        "",
        "KNOWN DATA ISSUES:",
        *all_issues[:30],
        "",
        "STORED PROCEDURES (with external calls):",
        *all_procs,
        "",
        "DATABASE LINKS (cross-system):",
        *all_db_links,
        "",
        "INTEGRATION INTERFACES:",
        *all_interfaces,
    ]

    return ParsedAsset(
        filename=filename,
        asset_type="json_schema",
        system_name=system,
        raw_summary=_truncate("\n".join(lines), 7000),
        metadata={"vendor": vendor, "version": version, "table_count": len(table_summaries)}
    )


# ── Remedy Ticket Log Parser ──────────────────────────────────────────────────

def parse_ticket_logs(filename: str, content: str) -> ParsedAsset:
    try:
        tickets = json.loads(content)
    except Exception:
        return ParsedAsset(filename=filename, asset_type="ticket_log",
                           system_name="Remedy ITSM", raw_summary=content[:3000])

    p1_p2 = [t for t in tickets if t.get("priority") in ("P1", "P2", "HIGH", "CRITICAL")]
    open_tickets = [t for t in tickets if t.get("status") == "OPEN"]
    recurring = [t for t in tickets if t.get("recurring")]

    summaries = []
    for t in tickets:
        systems = ", ".join(t.get("affected_systems", []))
        tags = ", ".join(t.get("tags", []))
        rec = " [RECURRING]" if t.get("recurring") else ""
        status = t.get("status", "")
        summaries.append(
            f"  [{t['ticket_id']}] {t['priority']} {t['type']}{rec} — {t['title']}\n"
            f"    Systems: {systems} | Status: {status}\n"
            f"    Root Cause: {t.get('root_cause', 'N/A')[:200]}\n"
            f"    Tags: {tags}"
        )

    lines = [
        f"SOURCE: Remedy ITSM Ticket Export ({len(tickets)} tickets)",
        f"HIGH/CRITICAL TICKETS: {len(p1_p2)}",
        f"OPEN/UNRESOLVED: {len(open_tickets)}",
        f"RECURRING ISSUES: {len(recurring)}",
        "",
        "TICKET DETAILS:",
        *summaries,
    ]

    return ParsedAsset(
        filename=filename,
        asset_type="ticket_log",
        system_name="Remedy ITSM",
        raw_summary="\n".join(lines),
        metadata={"total": len(tickets), "p1_p2": len(p1_p2), "open": len(open_tickets), "recurring": len(recurring)}
    )


# ── JIL Batch Schedule Parser ─────────────────────────────────────────────────

def parse_jil(filename: str, content: str) -> ParsedAsset:
    jobs = re.findall(r'insert_job:\s*(\S+)', content)
    boxes = re.findall(r'job_type:\s*BOX', content)
    conditions = re.findall(r'condition:\s*(.+)', content)
    machines = list(set(re.findall(r'machine:\s*(\S+)', content)))
    issues = re.findall(r'/\*\s*(KNOWN ISSUE|RISK|SECURITY|WARNING|NOTE|TODO|CRITICAL)[:\s](.+?)(?=\*/)', content, re.DOTALL | re.IGNORECASE)
    descriptions = re.findall(r'description:\s*"([^"]+)"', content)

    # Extract dependency chain
    dep_chain = []
    for cond in conditions:
        dep_chain.append(f"  {cond.strip()}")

    # Format issues
    issue_lines = []
    for tag, body in issues:
        clean = body.strip().replace('\n', ' ')[:200]
        issue_lines.append(f"  [{tag.upper()}] {clean}")

    lines = [
        f"SOURCE: Autosys JIL Batch Schedule",
        f"TOTAL JOBS: {len(jobs)}",
        f"BOX JOBS (orchestrators): {len(boxes)}",
        f"EXECUTION MACHINES: {', '.join(machines)}",
        "",
        f"JOB NAMES: {', '.join(jobs)}",
        "",
        "JOB DEPENDENCY CHAIN:",
        *dep_chain,
        "",
        f"JOB DESCRIPTIONS:",
        *[f"  {d}" for d in descriptions[:20]],
        "",
        "EMBEDDED WARNINGS & KNOWN ISSUES:",
        *issue_lines,
    ]

    return ParsedAsset(
        filename=filename,
        asset_type="jil_schedule",
        system_name="Billing Batch / Autosys",
        raw_summary=_truncate("\n".join(lines), 5000),
        metadata={"job_count": len(jobs), "machines": machines}
    )


# ── Dispatcher ───────────────────────────────────────────────────────────────

def parse_asset(filename: str, content: str) -> ParsedAsset:
    name_lower = filename.lower()
    content_stripped = content.strip()

    if name_lower.endswith((".yaml", ".yml")) or "swagger" in name_lower or "openapi" in name_lower:
        return parse_swagger(filename, content)
    elif name_lower.endswith(".sql"):
        return parse_sql_schema(filename, content)
    elif name_lower.endswith(".jil") or "jil" in name_lower or "batch" in name_lower:
        return parse_jil(filename, content)
    elif name_lower.endswith(".json"):
        # Distinguish CRM schema from ticket log
        if "ticket" in name_lower or "incident" in name_lower or "remedy" in name_lower:
            return parse_ticket_logs(filename, content)
        else:
            return parse_json_schema(filename, content)
    else:
        # Best-effort: peek at content
        if content_stripped.startswith("{") or content_stripped.startswith("["):
            try:
                data = json.loads(content)
                if isinstance(data, list) and data and "ticket_id" in data[0]:
                    return parse_ticket_logs(filename, content)
                return parse_json_schema(filename, content)
            except Exception:
                pass
        if "insert_job:" in content:
            return parse_jil(filename, content)
        if "CREATE TABLE" in content.upper():
            return parse_sql_schema(filename, content)
        if "swagger" in content.lower() or "openapi" in content.lower():
            return parse_swagger(filename, content)
        # Fallback
        return ParsedAsset(
            filename=filename,
            asset_type="unknown",
            system_name=filename,
            raw_summary=_truncate(content, 4000),
            metadata={}
        )


# ── Load pre-loaded assets from disk ─────────────────────────────────────────

def load_preloaded_assets() -> list[ParsedAsset]:
    # Support both local dev and Docker (/app is the WORKDIR in container)
    candidates = [
        Path(__file__).parent.parent / "assets",   # local: backend/parsers/../assets
        Path("/app/assets"),                         # Docker: /app/assets
        Path(__file__).parent / "assets",            # fallback
    ]
    assets_dir = next((p for p in candidates if p.exists()), candidates[0])
    results = []
    for path in sorted(assets_dir.iterdir()):
        if path.is_file() and not path.name.startswith("."):
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                asset = parse_asset(path.name, content)
                results.append(asset)
                print(f"[parsers] Loaded: {path.name} → {asset.asset_type} / {asset.system_name}")
            except Exception as e:
                print(f"[parsers] Failed to parse {path.name}: {e}")
    return results
