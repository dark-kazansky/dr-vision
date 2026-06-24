"""
Seed script — Insert sample workflows and jobs into PostgreSQL.

Usage:
    cd backend && python scripts/seed_data.py

Requires: PostgreSQL running on port 5433 with drvision database.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.workflow_repository import WorkflowRepository

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required.")
    print("Set it in your .env file or export it: export DATABASE_URL=postgresql://user:pass@localhost:5433/db")
    sys.exit(1)

# ─── Sample Workflows ─────────────────────────────────────────────────────────

WORKFLOWS = [
    {"name": "Invoice Processing", "description": "OCR → Classify → Extract invoice fields (amount, date, vendor)", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "invoice", "description": "Hóa đơn"}]}}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "amount", "type": "number"}, {"name": "date", "type": "string"}, {"name": "vendor", "type": "string"}]}}}]},
    {"name": "Contract Analysis", "description": "Parse PDF → Classify type → Extract key clauses and dates", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "contract", "description": "Hợp đồng"}]}}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "parties", "type": "string"}, {"name": "effective_date", "type": "string"}, {"name": "clauses", "type": "string"}]}}}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "expiry_date", "type": "string"}]}}}]},
    {"name": "Bank Statement Mining", "description": "Split pages → OCR → Extract transactions → Categorize spending", "steps": [{"type": "split", "tier": "Normal", "config": {"categories": [{"name": "transaction_page", "description": "Trang giao dịch"}]}}, {"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "date", "type": "string"}, {"name": "description", "type": "string"}, {"name": "amount", "type": "number"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "income", "description": "Thu nhập"}, {"doc_type": "expense", "description": "Chi tiêu"}]}}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "total_income", "type": "number"}, {"name": "total_expense", "type": "number"}]}}}]},
    {"name": "Receipt Scanner", "description": "Quick OCR → Extract total, date, store name", "steps": [{"type": "parse", "tier": "Rapid"}, {"type": "extract", "tier": "Rapid", "config": {"schema": {"fields": [{"name": "store", "type": "string"}, {"name": "total", "type": "number"}, {"name": "date", "type": "string"}]}}}]},
    {"name": "ID Document Verification", "description": "Parse ID card/passport → Extract personal info → Validate format", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "full_name", "type": "string"}, {"name": "id_number", "type": "string"}, {"name": "dob", "type": "string"}, {"name": "expiry", "type": "string"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "id_card", "description": "CMND/CCCD"}, {"doc_type": "passport", "description": "Hộ chiếu"}]}}]},
    {"name": "Medical Report Parser", "description": "OCR medical documents → Extract diagnosis, medications, lab results", "steps": [{"type": "parse", "tier": "Advance"}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "lab_result", "description": "Kết quả xét nghiệm"}, {"doc_type": "prescription", "description": "Đơn thuốc"}]}}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "diagnosis", "type": "string"}, {"name": "medications", "type": "string"}]}}}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "lab_values", "type": "string"}]}}}]},
    {"name": "Tax Form Extractor", "description": "Parse tax forms → Extract income, deductions, tax amounts", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "gross_income", "type": "number"}, {"name": "deductions", "type": "number"}, {"name": "tax_payable", "type": "number"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "personal_tax", "description": "Thuế TNCN"}, {"doc_type": "corporate_tax", "description": "Thuế TNDN"}]}}]},
    {"name": "Shipping Label Reader", "description": "OCR shipping labels → Extract sender, receiver, tracking number", "steps": [{"type": "parse", "tier": "Rapid"}, {"type": "extract", "tier": "Rapid", "config": {"schema": {"fields": [{"name": "sender", "type": "string"}, {"name": "receiver", "type": "string"}, {"name": "tracking_number", "type": "string"}]}}}]},
    {"name": "Resume/CV Parser", "description": "Parse resume → Extract skills, experience, education, contact info", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "name", "type": "string"}, {"name": "email", "type": "string"}, {"name": "skills", "type": "string"}, {"name": "experience", "type": "string"}]}}}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "education", "type": "string"}]}}}]},
    {"name": "Insurance Claim Processor", "description": "Classify claim type → Extract policy number, damage details, amounts", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "auto_claim", "description": "Bảo hiểm xe"}, {"doc_type": "health_claim", "description": "Bảo hiểm sức khỏe"}, {"doc_type": "property_claim", "description": "Bảo hiểm tài sản"}]}}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "policy_number", "type": "string"}, {"name": "claim_amount", "type": "number"}, {"name": "incident_date", "type": "string"}]}}}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "damage_description", "type": "string"}]}}}]},
    {"name": "Utility Bill Analyzer", "description": "OCR utility bills → Extract usage, charges, account number", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "account_number", "type": "string"}, {"name": "usage", "type": "number"}, {"name": "total_charge", "type": "number"}, {"name": "due_date", "type": "string"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "electric", "description": "Điện"}, {"doc_type": "water", "description": "Nước"}, {"doc_type": "internet", "description": "Internet"}]}}]},
    {"name": "Purchase Order Validator", "description": "Parse PO → Extract items, quantities, prices → Validate totals", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "po_number", "type": "string"}, {"name": "items", "type": "string"}, {"name": "subtotal", "type": "number"}, {"name": "tax", "type": "number"}, {"name": "total", "type": "number"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "valid", "description": "Hợp lệ"}, {"doc_type": "invalid", "description": "Không hợp lệ"}]}}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "validation_result", "type": "string"}]}}}]},
    {"name": "Passport MRZ Reader", "description": "OCR passport MRZ → Extract name, nationality, expiry date", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "surname", "type": "string"}, {"name": "given_names", "type": "string"}, {"name": "nationality", "type": "string"}, {"name": "passport_number", "type": "string"}, {"name": "expiry_date", "type": "string"}]}}}]},
    {"name": "Loan Application Review", "description": "Parse application → Extract income, assets, liabilities → Score", "steps": [{"type": "parse", "tier": "Advance"}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "applicant_name", "type": "string"}, {"name": "monthly_income", "type": "number"}, {"name": "total_assets", "type": "number"}, {"name": "total_liabilities", "type": "number"}]}}}, {"type": "classify", "tier": "Advance", "config": {"rules": [{"doc_type": "approved", "description": "Đủ điều kiện"}, {"doc_type": "rejected", "description": "Không đủ điều kiện"}, {"doc_type": "review", "description": "Cần xem xét thêm"}]}}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "credit_score", "type": "number"}, {"name": "recommendation", "type": "string"}]}}}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "risk_level", "type": "string"}]}}}]},
    {"name": "Delivery Note Processor", "description": "OCR delivery notes → Extract items delivered, signatures, dates", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "delivery_date", "type": "string"}, {"name": "items", "type": "string"}, {"name": "receiver_name", "type": "string"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "signed", "description": "Đã ký nhận"}, {"doc_type": "unsigned", "description": "Chưa ký"}]}}]},
    {"name": "Business Card Scanner", "description": "Quick OCR → Extract name, company, phone, email, address", "steps": [{"type": "parse", "tier": "Rapid"}, {"type": "extract", "tier": "Rapid", "config": {"schema": {"fields": [{"name": "name", "type": "string"}, {"name": "company", "type": "string"}, {"name": "phone", "type": "string"}, {"name": "email", "type": "string"}]}}}]},
    {"name": "Payslip Data Extractor", "description": "Parse payslips → Extract gross, net, deductions, employer info", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "employee_name", "type": "string"}, {"name": "gross_salary", "type": "number"}, {"name": "net_salary", "type": "number"}, {"name": "deductions", "type": "number"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "monthly", "description": "Lương tháng"}, {"doc_type": "bonus", "description": "Thưởng"}]}}]},
    {"name": "Vehicle Registration Parser", "description": "Parse registration docs → Extract plate, VIN, owner, expiry", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "plate_number", "type": "string"}, {"name": "vin", "type": "string"}, {"name": "owner_name", "type": "string"}, {"name": "registration_expiry", "type": "string"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "car", "description": "Ô tô"}, {"doc_type": "motorcycle", "description": "Xe máy"}]}}]},
    {"name": "Customs Declaration Form", "description": "OCR customs forms → Extract goods, values, origin country", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "goods_description", "type": "string"}, {"name": "declared_value", "type": "number"}, {"name": "origin_country", "type": "string"}, {"name": "hs_code", "type": "string"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "import", "description": "Nhập khẩu"}, {"doc_type": "export", "description": "Xuất khẩu"}]}}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "duty_amount", "type": "number"}]}}}]},
    {"name": "Rental Agreement Analyzer", "description": "Parse lease → Extract rent, duration, terms, parties involved", "steps": [{"type": "parse", "tier": "Normal"}, {"type": "extract", "tier": "Advance", "config": {"schema": {"fields": [{"name": "landlord", "type": "string"}, {"name": "tenant", "type": "string"}, {"name": "monthly_rent", "type": "number"}, {"name": "lease_start", "type": "string"}, {"name": "lease_end", "type": "string"}]}}}, {"type": "classify", "tier": "Normal", "config": {"rules": [{"doc_type": "residential", "description": "Nhà ở"}, {"doc_type": "commercial", "description": "Thương mại"}]}}, {"type": "extract", "tier": "Normal", "config": {"schema": {"fields": [{"name": "deposit", "type": "number"}, {"name": "terms", "type": "string"}]}}}]},
]

# ─── Sample Jobs ──────────────────────────────────────────────────────────────

def make_jobs(workflow_ids: dict) -> list:
    """Generate sample jobs referencing real workflow IDs."""
    now = datetime.now(timezone.utc)
    jobs = []

    def job(wf_key, status, progress, filename, nodes_data, error=None, offset_min=0, duration_sec=0):
        wf_id = workflow_ids.get(wf_key)
        wf_name = wf_key
        created = now - timedelta(minutes=offset_min)
        started = created + timedelta(seconds=1)
        completed = (started + timedelta(seconds=duration_sec)) if status in ('completed', 'failed') else None
        return {
            "workflow_id": wf_id,
            "workflow_name": wf_name,
            "status": status,
            "progress": progress,
            "nodes_data": nodes_data,
            "filename": filename,
            "file_count": 1,
            "max_retries": 3,
            "error": error,
            "created_at": created,
            "started_at": started,
            "completed_at": completed,
        }

    # Invoice Processing — multiple executions
    jobs.append(job("Invoice Processing", "completed", 1.0, "invoice_001.pdf",
        [{"node_id": "n1", "node_type": "parse", "node_label": "OCR", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "classify", "node_label": "Classify", "status": "completed", "retry_count": 0},
         {"node_id": "n3", "node_type": "extract", "node_label": "Extract", "status": "completed", "retry_count": 0}],
        offset_min=5, duration_sec=8))

    jobs.append(job("Invoice Processing", "completed", 1.0, "invoice_002.pdf",
        [{"node_id": "n1", "node_type": "parse", "node_label": "OCR", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "classify", "node_label": "Classify", "status": "completed", "retry_count": 0},
         {"node_id": "n3", "node_type": "extract", "node_label": "Extract", "status": "completed", "retry_count": 0}],
        offset_min=30, duration_sec=6))

    jobs.append(job("Invoice Processing", "failed", 0.33, "invoice_corrupt.pdf",
        [{"node_id": "n1", "node_type": "parse", "node_label": "OCR", "status": "failed", "retry_count": 3, "error": "PDF is corrupted"},
         {"node_id": "n2", "node_type": "classify", "node_label": "Classify", "status": "skipped", "retry_count": 0},
         {"node_id": "n3", "node_type": "extract", "node_label": "Extract", "status": "skipped", "retry_count": 0}],
        error="OCR failed: PDF is corrupted", offset_min=60, duration_sec=12))

    jobs.append(job("Invoice Processing", "running", 0.66, "invoice_batch.pdf",
        [{"node_id": "n1", "node_type": "parse", "node_label": "OCR", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "classify", "node_label": "Classify", "status": "completed", "retry_count": 0},
         {"node_id": "n3", "node_type": "extract", "node_label": "Extract", "status": "running", "retry_count": 0}],
        offset_min=1))

    # Contract Analysis
    jobs.append(job("Contract Analysis", "completed", 1.0, "contract_lease.pdf",
        [{"node_id": "n1", "node_type": "parse", "node_label": "Parse", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "classify", "node_label": "Classify", "status": "completed", "retry_count": 0},
         {"node_id": "n3", "node_type": "extract", "node_label": "Clauses", "status": "completed", "retry_count": 0},
         {"node_id": "n4", "node_type": "extract", "node_label": "Dates", "status": "completed", "retry_count": 0}],
        offset_min=120, duration_sec=15))

    jobs.append(job("Contract Analysis", "failed", 0.5, "contract_complex.pdf",
        [{"node_id": "n1", "node_type": "parse", "node_label": "Parse", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "classify", "node_label": "Classify", "status": "completed", "retry_count": 0},
         {"node_id": "n3", "node_type": "extract", "node_label": "Clauses", "status": "failed", "retry_count": 3, "error": "LLM timeout"},
         {"node_id": "n4", "node_type": "extract", "node_label": "Dates", "status": "skipped", "retry_count": 0}],
        error="Extract Clauses failed: LLM timeout", offset_min=90, duration_sec=20))

    # Bank Statement
    jobs.append(job("Bank Statement Mining", "completed", 1.0, "vietcombank_04_2026.pdf",
        [{"node_id": "n1", "node_type": "split", "node_label": "Split", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "parse", "node_label": "OCR", "status": "completed", "retry_count": 0},
         {"node_id": "n3", "node_type": "extract", "node_label": "Transactions", "status": "completed", "retry_count": 0},
         {"node_id": "n4", "node_type": "classify", "node_label": "Categorize", "status": "completed", "retry_count": 0},
         {"node_id": "n5", "node_type": "extract", "node_label": "Summary", "status": "completed", "retry_count": 0}],
        offset_min=45, duration_sec=25))

    jobs.append(job("Bank Statement Mining", "running", 0.4, "mbbank_05_2026.pdf",
        [{"node_id": "n1", "node_type": "split", "node_label": "Split", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "parse", "node_label": "OCR", "status": "completed", "retry_count": 0},
         {"node_id": "n3", "node_type": "extract", "node_label": "Transactions", "status": "running", "retry_count": 0},
         {"node_id": "n4", "node_type": "classify", "node_label": "Categorize", "status": "pending", "retry_count": 0},
         {"node_id": "n5", "node_type": "extract", "node_label": "Summary", "status": "pending", "retry_count": 0}],
        offset_min=2))

    # Receipt
    jobs.append(job("Receipt Scanner", "completed", 1.0, "receipt_highland.jpg",
        [{"node_id": "n1", "node_type": "parse", "node_label": "OCR", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "extract", "node_label": "Extract", "status": "completed", "retry_count": 0}],
        offset_min=15, duration_sec=3))

    # Medical
    jobs.append(job("Medical Report Parser", "completed", 1.0, "blood_test.pdf",
        [{"node_id": "n1", "node_type": "parse", "node_label": "OCR", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "classify", "node_label": "Type", "status": "completed", "retry_count": 0},
         {"node_id": "n3", "node_type": "extract", "node_label": "Lab Values", "status": "completed", "retry_count": 1},
         {"node_id": "n4", "node_type": "extract", "node_label": "Diagnosis", "status": "completed", "retry_count": 0}],
        offset_min=200, duration_sec=12))

    # Business Card
    jobs.append(job("Business Card Scanner", "completed", 1.0, "card_ceo.jpg",
        [{"node_id": "n1", "node_type": "parse", "node_label": "OCR", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "extract", "node_label": "Extract", "status": "completed", "retry_count": 0}],
        offset_min=10, duration_sec=2))

    jobs.append(job("Business Card Scanner", "failed", 0.5, "card_blurry.jpg",
        [{"node_id": "n1", "node_type": "parse", "node_label": "OCR", "status": "completed", "retry_count": 0},
         {"node_id": "n2", "node_type": "extract", "node_label": "Extract", "status": "failed", "retry_count": 3, "error": "Image too blurry"}],
        error="Extract failed: image too blurry", offset_min=8, duration_sec=5))

    return jobs


async def main():
    print("🌱 Seeding database...")
    print(f"   Database: {DATABASE_URL}")

    repo = WorkflowRepository(DATABASE_URL)
    await repo.connect()
    await repo.init_schema()

    # Insert workflows
    workflow_ids = {}
    print(f"\n📋 Inserting {len(WORKFLOWS)} workflows...")
    for wf in WORKFLOWS:
        steps = wf["steps"]
        graph_data = {"nodes": [], "edges": [], "steps": steps}
        result = await repo.create_workflow(
            name=wf["name"],
            description=wf["description"],
            graph_data=graph_data,
            status="published",
        )
        workflow_ids[wf["name"]] = result["workflow_id"]
        print(f"   ✓ {wf['name']} ({len(steps)} steps) → {result['workflow_id']}")

    # Insert jobs
    jobs_data = make_jobs(workflow_ids)
    print(f"\n🏃 Inserting {len(jobs_data)} jobs...")
    for j in jobs_data:
        nodes_data = j["nodes_data"]
        result = await repo.create_job(
            workflow_id=j["workflow_id"],
            workflow_name=j["workflow_name"],
            nodes_data=nodes_data,
            steps_data=None,
            filename=j["filename"],
            file_count=j["file_count"],
            max_retries=j["max_retries"],
        )
        # Update status, progress, timestamps
        await repo.update_job(
            job_id=result["job_id"],
            status=j["status"],
            progress=j["progress"],
            error=j.get("error"),
            started_at=j.get("started_at"),
            completed_at=j.get("completed_at"),
        )
        status_icon = {"completed": "✓", "failed": "✗", "running": "◉"}.get(j["status"], "○")
        print(f"   {status_icon} {j['workflow_name']} — {j['filename']} [{j['status']}]")

    await repo.close()
    print(f"\n✨ Done! {len(WORKFLOWS)} workflows + {len(jobs_data)} jobs inserted.")


if __name__ == "__main__":
    asyncio.run(main())
