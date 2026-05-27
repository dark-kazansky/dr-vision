"""
Realistic Seed Script — Populates DB with production-like data.

Simulates the full lifecycle:
1. Create canvases (user_canvas) with proper DSL
2. Create jobs linked to canvases (with realistic timestamps)
3. Create execution_states with node outputs
4. Create upload records with minio_path references

Usage:
    cd backend && python scripts/seed_realistic.py
"""

import asyncio
import json
import os
import sys
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.workflow_repository import WorkflowRepository

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://drvision:drvision_dev@localhost:5433/drvision"
)


def gen_id() -> str:
    return uuid.uuid4().hex[:32]


def gen_node_id() -> str:
    return f"node_{uuid.uuid4().hex[:8]}"


def build_dsl(nodes_def: List[Dict]) -> Dict[str, Any]:
    """Build a complete DSL from node definitions."""
    components = {}
    graph_nodes = []
    graph_edges = []
    path = []

    node_ids = [gen_node_id() for _ in nodes_def]
    path = list(node_ids)

    for i, (nid, ndef) in enumerate(zip(node_ids, nodes_def)):
        upstream = [node_ids[i - 1]] if i > 0 else []
        downstream = [node_ids[i + 1]] if i < len(node_ids) - 1 else []

        components[nid] = {
            "obj": {
                "component_name": ndef["component"],
                "params": ndef.get("params", {}),
            },
            "downstream": downstream,
            "upstream": upstream,
            "parent_id": None,
        }

        graph_nodes.append({
            "id": nid,
            "type": ndef["type"],
            "parentId": None,
            "position": {"x": 100 + i * 300, "y": 200},
            "data": {
                "label": ndef["label"],
                "name": ndef["component"],
                "form": ndef.get("params", {}),
            },
        })

    for i in range(len(node_ids) - 1):
        graph_edges.append({
            "id": f"edge_{node_ids[i]}_{node_ids[i+1]}",
            "source": node_ids[i],
            "target": node_ids[i + 1],
            "sourceHandle": "output",
            "targetHandle": "input",
        })

    return {
        "components": components,
        "graph": {"nodes": graph_nodes, "edges": graph_edges},
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


# ─── Canvas Definitions ───────────────────────────────────────────────────────

CANVASES = [
    {
        "title": "Invoice Processing",
        "desc": "Xử lý hóa đơn: OCR → Phân loại → Trích xuất thông tin",
        "category": "dataflow_canvas",
        "nodes": [
            {"type": "parse", "label": "OCR Scan", "component": "ParseProcessor", "params": {"tier": "Normal", "process_all_pages": True}},
            {"type": "classify", "label": "Phân loại", "component": "ClassifyProcessor", "params": {"tier": "Normal", "rules": [{"doc_type": "invoice", "description": "Hóa đơn VAT"}, {"doc_type": "receipt", "description": "Biên lai"}]}},
            {"type": "extract", "label": "Trích xuất", "component": "ExtractProcessor", "params": {"tier": "Normal", "schema": {"fields": [{"name": "invoice_number", "type": "string", "required": True}, {"name": "date", "type": "string", "required": True}, {"name": "vendor", "type": "string", "required": True}, {"name": "total_amount", "type": "number", "required": True}, {"name": "tax_amount", "type": "number"}]}}},
        ],
    },
    {
        "title": "Contract Analysis",
        "desc": "Phân tích hợp đồng: Parse → Classify → Extract clauses → Extract dates",
        "category": "dataflow_canvas",
        "nodes": [
            {"type": "parse", "label": "Parse PDF", "component": "ParseProcessor", "params": {"tier": "Advance", "parse_formatting": True}},
            {"type": "classify", "label": "Loại hợp đồng", "component": "ClassifyProcessor", "params": {"tier": "Normal", "rules": [{"doc_type": "lease", "description": "Hợp đồng thuê"}, {"doc_type": "service", "description": "Hợp đồng dịch vụ"}, {"doc_type": "employment", "description": "Hợp đồng lao động"}]}},
            {"type": "extract", "label": "Điều khoản", "component": "ExtractProcessor", "params": {"tier": "Advance", "schema": {"fields": [{"name": "parties", "type": "string", "required": True}, {"name": "obligations", "type": "string"}, {"name": "penalties", "type": "string"}]}}},
            {"type": "extract", "label": "Ngày tháng", "component": "ExtractProcessor", "params": {"tier": "Normal", "schema": {"fields": [{"name": "effective_date", "type": "string", "required": True}, {"name": "expiry_date", "type": "string", "required": True}, {"name": "renewal_terms", "type": "string"}]}}},
        ],
    },
    {
        "title": "Bank Statement Mining",
        "desc": "Khai thác sao kê ngân hàng: Split → OCR → Extract → Categorize → Summary",
        "category": "dataflow_canvas",
        "nodes": [
            {"type": "split", "label": "Tách trang", "component": "SplitProcessor", "params": {"tier": "Normal", "categories": [{"name": "transaction_page", "description": "Trang giao dịch", "order": 1}]}},
            {"type": "parse", "label": "OCR từng trang", "component": "ParseProcessor", "params": {"tier": "Normal", "process_all_pages": True}},
            {"type": "extract", "label": "Giao dịch", "component": "ExtractProcessor", "params": {"tier": "Normal", "schema": {"fields": [{"name": "date", "type": "string"}, {"name": "description", "type": "string"}, {"name": "debit", "type": "number"}, {"name": "credit", "type": "number"}, {"name": "balance", "type": "number"}]}}},
            {"type": "classify", "label": "Phân loại chi tiêu", "component": "ClassifyProcessor", "params": {"tier": "Normal", "rules": [{"doc_type": "food", "description": "Ăn uống"}, {"doc_type": "transport", "description": "Di chuyển"}, {"doc_type": "shopping", "description": "Mua sắm"}, {"doc_type": "bills", "description": "Hóa đơn"}, {"doc_type": "transfer", "description": "Chuyển khoản"}]}},
            {"type": "extract", "label": "Tổng hợp", "component": "ExtractProcessor", "params": {"tier": "Normal", "schema": {"fields": [{"name": "total_income", "type": "number"}, {"name": "total_expense", "type": "number"}, {"name": "net_change", "type": "number"}]}}},
        ],
    },
]


CANVASES += [
    {
        "title": "Receipt Scanner",
        "desc": "Quét hóa đơn nhanh: OCR → Extract thông tin cơ bản",
        "category": "dataflow_canvas",
        "nodes": [
            {"type": "parse", "label": "Quick OCR", "component": "ParseProcessor", "params": {"tier": "Rapid"}},
            {"type": "extract", "label": "Extract", "component": "ExtractProcessor", "params": {"tier": "Rapid", "schema": {"fields": [{"name": "store_name", "type": "string"}, {"name": "total", "type": "number"}, {"name": "date", "type": "string"}, {"name": "payment_method", "type": "string"}]}}},
        ],
    },
    {
        "title": "ID Document Verification",
        "desc": "Xác minh giấy tờ tùy thân: OCR → Extract → Validate",
        "category": "dataflow_canvas",
        "nodes": [
            {"type": "parse", "label": "OCR", "component": "ParseProcessor", "params": {"tier": "Normal"}},
            {"type": "extract", "label": "Thông tin cá nhân", "component": "ExtractProcessor", "params": {"tier": "Normal", "schema": {"fields": [{"name": "full_name", "type": "string", "required": True}, {"name": "id_number", "type": "string", "required": True}, {"name": "date_of_birth", "type": "string"}, {"name": "address", "type": "string"}, {"name": "expiry_date", "type": "string"}]}}},
            {"type": "classify", "label": "Loại giấy tờ", "component": "ClassifyProcessor", "params": {"tier": "Normal", "rules": [{"doc_type": "cccd", "description": "Căn cước công dân"}, {"doc_type": "cmnd", "description": "Chứng minh nhân dân"}, {"doc_type": "passport", "description": "Hộ chiếu"}, {"doc_type": "driving_license", "description": "Bằng lái xe"}]}},
        ],
    },
    {
        "title": "Medical Report Parser",
        "desc": "Phân tích kết quả y tế: OCR → Classify → Extract chẩn đoán + thuốc",
        "category": "dataflow_canvas",
        "nodes": [
            {"type": "parse", "label": "OCR", "component": "ParseProcessor", "params": {"tier": "Advance", "parse_formatting": True}},
            {"type": "classify", "label": "Loại báo cáo", "component": "ClassifyProcessor", "params": {"tier": "Normal", "rules": [{"doc_type": "blood_test", "description": "Xét nghiệm máu"}, {"doc_type": "imaging", "description": "Chẩn đoán hình ảnh"}, {"doc_type": "prescription", "description": "Đơn thuốc"}]}},
            {"type": "extract", "label": "Kết quả", "component": "ExtractProcessor", "params": {"tier": "Advance", "schema": {"fields": [{"name": "patient_name", "type": "string"}, {"name": "diagnosis", "type": "string"}, {"name": "medications", "type": "string"}, {"name": "lab_values", "type": "string"}, {"name": "doctor_name", "type": "string"}]}}},
        ],
    },
    {
        "title": "Tax Form Extractor",
        "desc": "Trích xuất tờ khai thuế: OCR → Extract thu nhập, khấu trừ, thuế",
        "category": "dataflow_canvas",
        "nodes": [
            {"type": "parse", "label": "OCR", "component": "ParseProcessor", "params": {"tier": "Normal"}},
            {"type": "extract", "label": "Thuế", "component": "ExtractProcessor", "params": {"tier": "Advance", "schema": {"fields": [{"name": "taxpayer_name", "type": "string"}, {"name": "tax_id", "type": "string"}, {"name": "gross_income", "type": "number"}, {"name": "deductions", "type": "number"}, {"name": "tax_payable", "type": "number"}]}}},
        ],
    },
    {
        "title": "Shipping Label Reader",
        "desc": "Đọc nhãn vận chuyển: OCR nhanh → Extract thông tin gửi/nhận",
        "category": "dataflow_canvas",
        "nodes": [
            {"type": "parse", "label": "OCR", "component": "ParseProcessor", "params": {"tier": "Rapid"}},
            {"type": "extract", "label": "Extract", "component": "ExtractProcessor", "params": {"tier": "Rapid", "schema": {"fields": [{"name": "sender_name", "type": "string"}, {"name": "sender_address", "type": "string"}, {"name": "receiver_name", "type": "string"}, {"name": "receiver_address", "type": "string"}, {"name": "tracking_number", "type": "string"}, {"name": "weight", "type": "string"}]}}},
        ],
    },
    {
        "title": "Resume/CV Parser",
        "desc": "Phân tích CV: Parse → Extract kỹ năng, kinh nghiệm, học vấn",
        "category": "dataflow_canvas",
        "nodes": [
            {"type": "parse", "label": "Parse CV", "component": "ParseProcessor", "params": {"tier": "Normal", "parse_formatting": True}},
            {"type": "extract", "label": "Thông tin", "component": "ExtractProcessor", "params": {"tier": "Advance", "schema": {"fields": [{"name": "full_name", "type": "string"}, {"name": "email", "type": "string"}, {"name": "phone", "type": "string"}, {"name": "skills", "type": "string"}, {"name": "experience_years", "type": "number"}, {"name": "education", "type": "string"}, {"name": "languages", "type": "string"}]}}},
        ],
    },
    {
        "title": "Insurance Claim Processor",
        "desc": "Xử lý yêu cầu bảo hiểm: OCR → Classify loại → Extract chi tiết",
        "category": "agent_canvas",
        "nodes": [
            {"type": "parse", "label": "OCR", "component": "ParseProcessor", "params": {"tier": "Normal"}},
            {"type": "classify", "label": "Loại claim", "component": "ClassifyProcessor", "params": {"tier": "Normal", "rules": [{"doc_type": "auto", "description": "Bảo hiểm xe"}, {"doc_type": "health", "description": "Bảo hiểm sức khỏe"}, {"doc_type": "property", "description": "Bảo hiểm tài sản"}, {"doc_type": "life", "description": "Bảo hiểm nhân thọ"}]}},
            {"type": "extract", "label": "Chi tiết", "component": "ExtractProcessor", "params": {"tier": "Advance", "schema": {"fields": [{"name": "policy_number", "type": "string", "required": True}, {"name": "insured_name", "type": "string"}, {"name": "incident_date", "type": "string"}, {"name": "claim_amount", "type": "number"}, {"name": "damage_description", "type": "string"}]}}},
        ],
    },
]


# ─── Job Simulation ───────────────────────────────────────────────────────────

def simulate_job_execution(canvas_title: str, canvas_id: str, dsl: Dict, filename: str,
                           status: str, offset_minutes: int, duration_sec: int) -> Dict:
    """Simulate a realistic job execution with proper node states."""
    now = datetime.now(timezone.utc)
    created = now - timedelta(minutes=offset_minutes)
    started = created + timedelta(seconds=2)

    path = dsl.get("path", [])
    nodes_data = []
    node_outputs = {}

    if status == "completed":
        # All nodes completed
        elapsed = 0
        for i, nid in enumerate(path):
            comp = dsl["components"][nid]
            node_dur = duration_sec // len(path)
            nodes_data.append({
                "node_id": nid,
                "node_type": comp["obj"]["component_name"].replace("Processor", "").lower(),
                "node_label": dsl["graph"]["nodes"][i]["data"]["label"],
                "status": "completed",
                "retry_count": 0,
                "error": None,
                "config": comp["obj"]["params"],
                "tier": comp["obj"]["params"].get("tier", "Normal"),
            })
            node_outputs[nid] = {
                "output": {"success": True, "text": f"Processed by {comp['obj']['component_name']}"},
                "status": "completed",
                "duration_ms": node_dur * 1000,
                "saved_at": (started + timedelta(seconds=elapsed + node_dur)).isoformat(),
            }
            elapsed += node_dur
        completed_at = started + timedelta(seconds=duration_sec)
    elif status == "failed":
        # Fail at a middle node
        fail_idx = len(path) // 2
        elapsed = 0
        for i, nid in enumerate(path):
            comp = dsl["components"][nid]
            node_dur = duration_sec // len(path)
            if i < fail_idx:
                ns = "completed"
                err = None
            elif i == fail_idx:
                ns = "failed"
                err = "LLM timeout: model did not respond within 30s"
            else:
                ns = "skipped"
                err = None
            nodes_data.append({
                "node_id": nid,
                "node_type": comp["obj"]["component_name"].replace("Processor", "").lower(),
                "node_label": dsl["graph"]["nodes"][i]["data"]["label"],
                "status": ns,
                "retry_count": 3 if ns == "failed" else 0,
                "error": err,
                "config": comp["obj"]["params"],
                "tier": comp["obj"]["params"].get("tier", "Normal"),
            })
            if ns == "completed":
                node_outputs[nid] = {
                    "output": {"success": True, "text": f"OK"},
                    "status": "completed",
                    "duration_ms": node_dur * 1000,
                    "saved_at": (started + timedelta(seconds=elapsed + node_dur)).isoformat(),
                }
            elif ns == "failed":
                node_outputs[nid] = {
                    "output": None,
                    "status": "failed",
                    "error": err,
                    "duration_ms": node_dur * 1000,
                    "saved_at": (started + timedelta(seconds=elapsed + node_dur)).isoformat(),
                }
            elapsed += node_dur
        completed_at = started + timedelta(seconds=duration_sec)
    else:  # running
        run_idx = len(path) // 2
        elapsed = 0
        for i, nid in enumerate(path):
            comp = dsl["components"][nid]
            node_dur = 5
            if i < run_idx:
                ns = "completed"
            elif i == run_idx:
                ns = "running"
            else:
                ns = "pending"
            nodes_data.append({
                "node_id": nid,
                "node_type": comp["obj"]["component_name"].replace("Processor", "").lower(),
                "node_label": dsl["graph"]["nodes"][i]["data"]["label"],
                "status": ns,
                "retry_count": 0,
                "error": None,
                "config": comp["obj"]["params"],
                "tier": comp["obj"]["params"].get("tier", "Normal"),
            })
            if ns == "completed":
                node_outputs[nid] = {
                    "output": {"success": True, "text": f"OK"},
                    "status": "completed",
                    "duration_ms": node_dur * 1000,
                    "saved_at": (started + timedelta(seconds=elapsed + node_dur)).isoformat(),
                }
            elapsed += node_dur
        completed_at = None

    progress = sum(1 for n in nodes_data if n["status"] == "completed") / len(nodes_data) if nodes_data else 0

    return {
        "canvas_id": canvas_id,
        "canvas_title": canvas_title,
        "filename": filename,
        "status": status,
        "progress": round(progress, 2),
        "nodes_data": nodes_data,
        "node_outputs": node_outputs,
        "error": nodes_data[len(path)//2]["error"] if status == "failed" else None,
        "created_at": created,
        "started_at": started,
        "completed_at": completed_at,
        "minio_path": f"jobs/{filename}",
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    print("🌱 Realistic seed — full lifecycle simulation")
    print(f"   Database: {DATABASE_URL}\n")

    repo = WorkflowRepository(DATABASE_URL)
    await repo.connect()
    await repo.init_schema()

    # Clean slate
    async with repo._pool.acquire() as conn:
        await conn.execute("DELETE FROM execution_states")
        await conn.execute("DELETE FROM uploads")
        await conn.execute("DELETE FROM job_logs")
        await conn.execute("DELETE FROM jobs")
        await conn.execute("DELETE FROM user_canvas_version")
        await conn.execute("DELETE FROM user_canvas")
    print("   ✓ Cleared all existing data\n")

    # ── Step 1: Create canvases ──
    print(f"📋 Creating {len(CANVASES)} canvases...")
    canvas_map = {}  # title → {id, dsl}
    for c in CANVASES:
        dsl = build_dsl(c["nodes"])
        result = await repo.create_canvas(
            title=c["title"],
            user_id="admin",
            canvas_category=c["category"],
            description=c["desc"],
            dsl=dsl,
        )
        canvas_map[c["title"]] = {"id": result["id"], "dsl": dsl}
        print(f"   ✓ {c['title']} ({len(c['nodes'])} nodes)")

    # ── Step 2: Publish versions for some ──
    print(f"\n📦 Publishing versions...")
    for title in ["Invoice Processing", "Contract Analysis", "Bank Statement Mining",
                  "Receipt Scanner", "ID Document Verification", "Medical Report Parser"]:
        ver = await repo.publish_canvas_version(canvas_map[title]["id"], title="v1.0")
        print(f"   ✓ {title} → {ver['id'][:12]}...")

    # ── Step 3: Create jobs with realistic execution ──
    print(f"\n🏃 Creating jobs...")
    job_scenarios = [
        ("Invoice Processing", "completed", "hoadon_vat_001.pdf", 5, 8),
        ("Invoice Processing", "completed", "hoadon_vat_002.pdf", 25, 6),
        ("Invoice Processing", "completed", "invoice_march_2026.pdf", 120, 7),
        ("Invoice Processing", "failed", "hoadon_scan_blur.pdf", 45, 10),
        ("Invoice Processing", "running", "invoice_batch_may.pdf", 1, 0),
        ("Contract Analysis", "completed", "hopdong_thue_nha.pdf", 60, 18),
        ("Contract Analysis", "completed", "hopdong_lao_dong.pdf", 180, 15),
        ("Contract Analysis", "failed", "contract_100pages.pdf", 30, 25),
        ("Bank Statement Mining", "completed", "vcb_042026.pdf", 90, 30),
        ("Bank Statement Mining", "completed", "tcb_052026.pdf", 200, 28),
        ("Bank Statement Mining", "running", "mb_052026.pdf", 2, 0),
        ("Receipt Scanner", "completed", "receipt_highland.jpg", 10, 3),
        ("Receipt Scanner", "completed", "receipt_grab_food.png", 15, 2),
        ("ID Document Verification", "completed", "cccd_front.jpg", 8, 5),
        ("ID Document Verification", "failed", "id_blurry_photo.jpg", 12, 6),
        ("Medical Report Parser", "completed", "xetnghiem_mau.pdf", 50, 12),
        ("Medical Report Parser", "completed", "sieu_am_bung.pdf", 300, 10),
        ("Tax Form Extractor", "completed", "tokhai_thue_2025.pdf", 150, 9),
        ("Shipping Label Reader", "completed", "nhan_ghn.jpg", 3, 2),
        ("Resume/CV Parser", "completed", "cv_nguyen_van_a.pdf", 20, 7),
        ("Insurance Claim Processor", "completed", "claim_xe_tai_nan.pdf", 100, 14),
        ("Insurance Claim Processor", "failed", "claim_incomplete.pdf", 70, 8),
    ]

    for title, status, filename, offset, duration in job_scenarios:
        cdata = canvas_map[title]
        sim = simulate_job_execution(title, cdata["id"], cdata["dsl"], filename, status, offset, duration)

        # Create job in DB
        result = await repo.create_job(
            workflow_id=None,  # Legacy FK, not used
            workflow_name=title,
            nodes_data=sim["nodes_data"],
            steps_data=[{"type": n["node_type"], "tier": n.get("tier", "Normal"), "config": n.get("config")} for n in sim["nodes_data"]],
            filename=filename,
            file_count=1,
            max_retries=3,
        )
        job_id = result["job_id"]

        # Update status + timestamps
        await repo.update_job(
            job_id=job_id,
            status=sim["status"],
            progress=sim["progress"],
            error=sim["error"],
            started_at=sim["started_at"],
            completed_at=sim["completed_at"],
        )

        # Set minio path
        await repo.set_job_minio_path(job_id, sim["minio_path"])

        # Create execution state
        await repo.create_execution_state(job_id=job_id, workflow_id=None)
        if sim["node_outputs"]:
            await repo.update_execution_state(
                job_id=job_id,
                node_states=sim["node_outputs"],
                status=sim["status"],
            )

        # Create upload record
        await repo.create_upload(
            job_id=job_id,
            filename=filename,
            minio_path=sim["minio_path"],
            size_bytes=len(filename) * 50000,  # Fake size
            mime_type="application/pdf" if filename.endswith(".pdf") else "image/jpeg",
        )

        icon = {"completed": "✓", "failed": "✗", "running": "◉"}[status]
        print(f"   {icon} {title} — {filename} [{status}]")

    await repo.close()
    print(f"\n✨ Done! {len(CANVASES)} canvases + {len(job_scenarios)} jobs with full execution state.")


if __name__ == "__main__":
    asyncio.run(main())
