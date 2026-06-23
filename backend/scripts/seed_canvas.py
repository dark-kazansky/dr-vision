"""
Seed script — Insert sample canvases (workflows) and jobs into PostgreSQL
using the new user_canvas schema.

Usage:
    cd backend && python scripts/seed_canvas.py

Requires: PostgreSQL running on port 5433 with drvision database.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.workflow_repository import WorkflowRepository

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required.")
    print("Set it in your .env file or export it: export DATABASE_URL=postgresql://user:pass@localhost:5433/db")
    sys.exit(1)


def make_dsl(steps):
    """Build a DSL structure from a list of step definitions."""
    components = {}
    nodes = []
    edges = []
    path = []

    for i, step in enumerate(steps):
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        path.append(node_id)

        # Component
        components[node_id] = {
            "obj": {
                "component_name": f"{step['type'].capitalize()}Processor",
                "params": {
                    "tier": step.get("tier", "Normal"),
                    **(step.get("config") or {}),
                },
            },
            "downstream": [],
            "upstream": [],
            "parent_id": None,
        }

        # Graph node
        nodes.append({
            "id": node_id,
            "type": step["type"],
            "parentId": None,
            "data": {
                "label": step.get("label", step["type"].capitalize()),
                "name": f"{step['type'].capitalize()}Processor",
                "form": step.get("config") or {},
            },
        })

    # Build edges and upstream/downstream
    for i in range(len(path) - 1):
        src = path[i]
        tgt = path[i + 1]
        edges.append({"id": f"edge_{src}_{tgt}", "source": src, "target": tgt})
        components[src]["downstream"].append(tgt)
        components[tgt]["upstream"].append(src)

    return {
        "components": components,
        "graph": {"nodes": nodes, "edges": edges},
        "globals": {
            "sys.query": "",
            "sys.conversation_turns": 0,
            "sys.files": [],
            "sys.history": [],
        },
        "path": path,
        "history": [],
        "variables": {},
    }


CANVASES = [
    {"title": "Invoice Processing", "description": "OCR → Classify → Extract invoice fields (amount, date, vendor)", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "OCR"}, {"type": "classify", "tier": "Normal", "label": "Classify", "config": {"rules": [{"doc_type": "invoice", "description": "Hóa đơn"}]}}, {"type": "extract", "tier": "Normal", "label": "Extract Fields", "config": {"schema": {"fields": [{"name": "amount", "type": "number"}, {"name": "date", "type": "string"}, {"name": "vendor", "type": "string"}]}}}]},
    {"title": "Contract Analysis", "description": "Parse PDF → Classify type → Extract key clauses and dates", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "Parse PDF"}, {"type": "classify", "tier": "Normal", "label": "Classify Type", "config": {"rules": [{"doc_type": "contract", "description": "Hợp đồng"}]}}, {"type": "extract", "tier": "Advance", "label": "Extract Clauses", "config": {"schema": {"fields": [{"name": "parties", "type": "string"}, {"name": "clauses", "type": "string"}]}}}, {"type": "extract", "tier": "Advance", "label": "Extract Dates", "config": {"schema": {"fields": [{"name": "effective_date", "type": "string"}, {"name": "expiry_date", "type": "string"}]}}}]},
    {"title": "Bank Statement Mining", "description": "Split pages → OCR → Extract transactions → Categorize spending", "category": "dataflow_canvas", "steps": [{"type": "split", "tier": "Normal", "label": "Split Pages", "config": {"categories": [{"name": "transaction_page"}]}}, {"type": "parse", "tier": "Normal", "label": "OCR Pages"}, {"type": "extract", "tier": "Normal", "label": "Extract Transactions", "config": {"schema": {"fields": [{"name": "date", "type": "string"}, {"name": "description", "type": "string"}, {"name": "amount", "type": "number"}]}}}, {"type": "classify", "tier": "Normal", "label": "Categorize", "config": {"rules": [{"doc_type": "income"}, {"doc_type": "expense"}]}}, {"type": "extract", "tier": "Normal", "label": "Summary", "config": {"schema": {"fields": [{"name": "total_income", "type": "number"}, {"name": "total_expense", "type": "number"}]}}}]},
    {"title": "Receipt Scanner", "description": "Quick OCR → Extract total, date, store name", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Rapid", "label": "Quick OCR"}, {"type": "extract", "tier": "Rapid", "label": "Extract Info", "config": {"schema": {"fields": [{"name": "store", "type": "string"}, {"name": "total", "type": "number"}, {"name": "date", "type": "string"}]}}}]},
    {"title": "ID Document Verification", "description": "Parse ID card/passport → Extract personal info → Validate", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "OCR"}, {"type": "extract", "tier": "Normal", "label": "Extract Info", "config": {"schema": {"fields": [{"name": "full_name", "type": "string"}, {"name": "id_number", "type": "string"}, {"name": "dob", "type": "string"}]}}}, {"type": "classify", "tier": "Normal", "label": "Validate", "config": {"rules": [{"doc_type": "id_card"}, {"doc_type": "passport"}]}}]},
    {"title": "Medical Report Parser", "description": "OCR medical documents → Extract diagnosis, medications, lab results", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Advance", "label": "OCR"}, {"type": "classify", "tier": "Normal", "label": "Report Type", "config": {"rules": [{"doc_type": "lab_result"}, {"doc_type": "prescription"}]}}, {"type": "extract", "tier": "Advance", "label": "Extract Data", "config": {"schema": {"fields": [{"name": "diagnosis", "type": "string"}, {"name": "medications", "type": "string"}, {"name": "lab_values", "type": "string"}]}}}]},
    {"title": "Tax Form Extractor", "description": "Parse tax forms → Extract income, deductions, tax amounts", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "OCR"}, {"type": "extract", "tier": "Advance", "label": "Extract", "config": {"schema": {"fields": [{"name": "gross_income", "type": "number"}, {"name": "deductions", "type": "number"}, {"name": "tax_payable", "type": "number"}]}}}]},
    {"title": "Shipping Label Reader", "description": "OCR shipping labels → Extract sender, receiver, tracking", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Rapid", "label": "OCR"}, {"type": "extract", "tier": "Rapid", "label": "Extract", "config": {"schema": {"fields": [{"name": "sender", "type": "string"}, {"name": "receiver", "type": "string"}, {"name": "tracking_number", "type": "string"}]}}}]},
    {"title": "Resume/CV Parser", "description": "Parse resume → Extract skills, experience, education", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "Parse"}, {"type": "extract", "tier": "Advance", "label": "Extract Skills", "config": {"schema": {"fields": [{"name": "name", "type": "string"}, {"name": "skills", "type": "string"}, {"name": "experience", "type": "string"}, {"name": "education", "type": "string"}]}}}]},
    {"title": "Insurance Claim Processor", "description": "Classify claim → Extract policy, damage, amounts", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "OCR"}, {"type": "classify", "tier": "Normal", "label": "Claim Type", "config": {"rules": [{"doc_type": "auto_claim"}, {"doc_type": "health_claim"}]}}, {"type": "extract", "tier": "Advance", "label": "Extract", "config": {"schema": {"fields": [{"name": "policy_number", "type": "string"}, {"name": "claim_amount", "type": "number"}]}}}]},
    {"title": "Utility Bill Analyzer", "description": "OCR utility bills → Extract usage, charges, account", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "OCR"}, {"type": "extract", "tier": "Normal", "label": "Extract", "config": {"schema": {"fields": [{"name": "account_number", "type": "string"}, {"name": "usage", "type": "number"}, {"name": "total_charge", "type": "number"}]}}}]},
    {"title": "Purchase Order Validator", "description": "Parse PO → Extract items → Validate totals", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "Parse"}, {"type": "extract", "tier": "Normal", "label": "Extract Items", "config": {"schema": {"fields": [{"name": "po_number", "type": "string"}, {"name": "items", "type": "string"}, {"name": "total", "type": "number"}]}}}, {"type": "classify", "tier": "Normal", "label": "Validate", "config": {"rules": [{"doc_type": "valid"}, {"doc_type": "invalid"}]}}]},
    {"title": "Passport MRZ Reader", "description": "OCR passport MRZ → Extract name, nationality, expiry", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "OCR MRZ"}, {"type": "extract", "tier": "Normal", "label": "Extract", "config": {"schema": {"fields": [{"name": "surname", "type": "string"}, {"name": "nationality", "type": "string"}, {"name": "passport_number", "type": "string"}, {"name": "expiry_date", "type": "string"}]}}}]},
    {"title": "Loan Application Review", "description": "Parse → Extract financials → Score creditworthiness", "category": "agent_canvas", "steps": [{"type": "parse", "tier": "Advance", "label": "Parse"}, {"type": "extract", "tier": "Advance", "label": "Financials", "config": {"schema": {"fields": [{"name": "monthly_income", "type": "number"}, {"name": "total_assets", "type": "number"}, {"name": "total_liabilities", "type": "number"}]}}}, {"type": "classify", "tier": "Advance", "label": "Score", "config": {"rules": [{"doc_type": "approved"}, {"doc_type": "rejected"}, {"doc_type": "review"}]}}]},
    {"title": "Delivery Note Processor", "description": "OCR delivery notes → Extract items, signatures, dates", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "OCR"}, {"type": "extract", "tier": "Normal", "label": "Extract", "config": {"schema": {"fields": [{"name": "delivery_date", "type": "string"}, {"name": "items", "type": "string"}, {"name": "receiver_name", "type": "string"}]}}}]},
    {"title": "Business Card Scanner", "description": "Quick OCR → Extract name, company, phone, email", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Rapid", "label": "OCR"}, {"type": "extract", "tier": "Rapid", "label": "Extract", "config": {"schema": {"fields": [{"name": "name", "type": "string"}, {"name": "company", "type": "string"}, {"name": "phone", "type": "string"}, {"name": "email", "type": "string"}]}}}]},
    {"title": "Payslip Data Extractor", "description": "Parse payslips → Extract gross, net, deductions", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "Parse"}, {"type": "extract", "tier": "Normal", "label": "Extract", "config": {"schema": {"fields": [{"name": "gross_salary", "type": "number"}, {"name": "net_salary", "type": "number"}, {"name": "deductions", "type": "number"}]}}}]},
    {"title": "Vehicle Registration Parser", "description": "Parse registration → Extract plate, VIN, owner", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "OCR"}, {"type": "extract", "tier": "Normal", "label": "Extract", "config": {"schema": {"fields": [{"name": "plate_number", "type": "string"}, {"name": "vin", "type": "string"}, {"name": "owner_name", "type": "string"}]}}}]},
    {"title": "Customs Declaration Form", "description": "OCR customs forms → Extract goods, values, origin", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "OCR"}, {"type": "extract", "tier": "Advance", "label": "Extract", "config": {"schema": {"fields": [{"name": "goods_description", "type": "string"}, {"name": "declared_value", "type": "number"}, {"name": "origin_country", "type": "string"}]}}}, {"type": "classify", "tier": "Normal", "label": "Type", "config": {"rules": [{"doc_type": "import"}, {"doc_type": "export"}]}}]},
    {"title": "Rental Agreement Analyzer", "description": "Parse lease → Extract rent, duration, terms, parties", "category": "dataflow_canvas", "steps": [{"type": "parse", "tier": "Normal", "label": "Parse"}, {"type": "extract", "tier": "Advance", "label": "Extract Terms", "config": {"schema": {"fields": [{"name": "landlord", "type": "string"}, {"name": "tenant", "type": "string"}, {"name": "monthly_rent", "type": "number"}, {"name": "lease_start", "type": "string"}, {"name": "lease_end", "type": "string"}]}}}]},
]


async def main():
    print("🌱 Seeding user_canvas table...")
    print(f"   Database: {DATABASE_URL}")

    repo = WorkflowRepository(DATABASE_URL)
    await repo.connect()
    await repo.init_schema()

    # Clear existing canvas data
    async with repo._pool.acquire() as conn:
        await conn.execute("DELETE FROM user_canvas_version")
        await conn.execute("DELETE FROM user_canvas")
    print("   Cleared existing canvas data.")

    # Insert canvases
    canvas_ids = {}
    print(f"\n📋 Inserting {len(CANVASES)} canvases...")
    for c in CANVASES:
        dsl = make_dsl(c["steps"])
        result = await repo.create_canvas(
            title=c["title"],
            user_id="default",
            canvas_category=c.get("category", "dataflow_canvas"),
            description=c["description"],
            dsl=dsl,
        )
        canvas_ids[c["title"]] = result["id"]
        step_count = len(c["steps"])
        print(f"   ✓ {c['title']} ({step_count} nodes) → {result['id']}")

    # Publish some as versions
    published = ["Invoice Processing", "Contract Analysis", "Bank Statement Mining",
                 "Receipt Scanner", "Business Card Scanner", "Medical Report Parser"]
    print(f"\n📦 Publishing {len(published)} versions...")
    for name in published:
        cid = canvas_ids[name]
        ver = await repo.publish_canvas_version(cid, title="v1.0")
        if ver:
            print(f"   ✓ {name} → version {ver['id']}")

    await repo.close()
    print(f"\n✨ Done! {len(CANVASES)} canvases inserted into user_canvas table.")


if __name__ == "__main__":
    asyncio.run(main())
