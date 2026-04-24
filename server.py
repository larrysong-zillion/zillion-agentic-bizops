"""
Zillion Network — AI Proposal Engine Backend
=============================================
FastAPI server providing:
  1. Claude API proxy (keeps API key server-side)
  2. SQLite persistence for proposals
  3. Edit delta logging for RLHF fine-tuning signal
  4. Inventory API (Google Sheets integration stub)
  5. CORS for Netlify frontend
 
Run: uvicorn server:app --host 0.0.0.0 --port 8000
Env: ANTHROPIC_API_KEY=sk-ant-...
"""
 
import os, json, sqlite3, hashlib, time
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from typing import Optional
 
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
 
import httpx
 
# ═══ CONFIG ═══
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"
DB_PATH = Path("zillion.db")
# Simple auth token — set ZN_AUTH_TOKEN env var, or defaults to hash of API key
AUTH_TOKEN = os.getenv("ZN_AUTH_TOKEN", hashlib.sha256((ANTHROPIC_API_KEY or "zillion").encode()).hexdigest()[:32])
 
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
 
app = FastAPI(title="Zillion Proposal Engine API", version="1.1")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# ═══ AUTH ═══
async def verify_token(authorization: Optional[str] = Header(None)):
    if not AUTH_TOKEN:
        return True
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    if authorization.split(" ", 1)[1] != AUTH_TOKEN:
        raise HTTPException(403, "Invalid token")
    return True
 
# ═══ DATABASE ═══
def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS proposals (
            id TEXT PRIMARY KEY,
            client TEXT NOT NULL,
            amount TEXT,
            date TEXT,
            status TEXT DEFAULT 'pending',
            text TEXT,
            saved_text TEXT,
            notes TEXT DEFAULT '',
            followup TEXT,
            confidence_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL,
            label TEXT,
            text TEXT,
            is_current INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS edit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL,
            agent TEXT,
            original_text TEXT,
            edited_text TEXT,
            deal_outcome TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT PRIMARY KEY,
            name TEXT,
            gpu TEXT,
            gpu_mem INTEGER,
            vram INTEGER,
            price REAL,
            stock INTEGER,
            rack_u INTEGER,
            power REAL,
            nvlink TEXT,
            fp16 REAL,
            colo REAL,
            arch TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS fleet_servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT UNIQUE,
            model TEXT,
            dc TEXT,
            rack TEXT,
            status TEXT DEFAULT 'Rental',
            assigned_to TEXT DEFAULT '',
            cpu TEXT,
            memory TEXT,
            ip TEXT,
            os TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
 
@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
 
# ═══ RATE LIMITING ═══
_rate_store = {}  # ip -> [timestamp, timestamp, ...]
RATE_LIMIT = 20  # requests per minute
RATE_WINDOW = 60  # seconds
 
def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    if ip not in _rate_store:
        _rate_store[ip] = []
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < RATE_WINDOW]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        raise HTTPException(429, f"Rate limit exceeded. Max {RATE_LIMIT} requests per minute.")
    _rate_store[ip].append(now)
 
# ═══ INPUT SANITIZATION ═══
MAX_PROMPT_LENGTH = 50000  # 50KB max per prompt field
BLOCKED_PATTERNS = ["ignore above", "forget instructions", "system prompt", "you are now"]
 
def sanitize_prompt(text: str) -> str:
    if len(text) > MAX_PROMPT_LENGTH:
        text = text[:MAX_PROMPT_LENGTH]
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in text.lower():
            text = text.replace(pattern, "[filtered]")
    return text
 
# ═══ MODELS ═══
class AgentRequest(BaseModel):
    system_prompt: str
    user_message: str
    max_tokens: int = 4000
 
class ProposalCreate(BaseModel):
    id: str
    client: str
    amount: Optional[str] = None
    date: Optional[str] = None
    status: str = "pending"
    text: str = ""
    notes: str = ""
    followup: Optional[str] = None
    confidence: Optional[dict] = None
    versions: Optional[list] = None
 
class ProposalUpdate(BaseModel):
    status: Optional[str] = None
    text: Optional[str] = None
    notes: Optional[str] = None
    followup: Optional[str] = None
 
class EditLogEntry(BaseModel):
    proposal_id: str
    agent: str
    original_text: str
    edited_text: str
    deal_outcome: Optional[str] = None
 
class InventoryItem(BaseModel):
    sku: str
    name: str
    gpu: str
    gpu_mem: int
    vram: int
    price: float
    stock: int
    rack_u: int
    power: float
    nvlink: str
    fp16: float
    colo: float
    arch: str
 
# ═══ CLAUDE API PROXY ═══
@app.post("/api/agent/{agent_name}")
async def run_agent(agent_name: str, req: AgentRequest, request: Request, _=Depends(verify_token)):
    check_rate_limit(request)
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY not configured")
    if agent_name not in ("discovery", "architect", "writer"):
        raise HTTPException(400, f"Unknown agent: {agent_name}")
 
    # Sanitize inputs
    system = sanitize_prompt(req.system_prompt)
    user_msg = sanitize_prompt(req.user_message)
    max_tok = min(req.max_tokens, 8000)  # Cap tokens
 
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                ANTHROPIC_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": MODEL,
                    "max_tokens": max_tok,
                    "system": system,
                    "messages": [{"role": "user", "content": user_msg}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = "".join(b.get("text", "") for b in data.get("content", []))
            return {"text": text, "model": MODEL, "agent": agent_name}
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, f"Anthropic API error: {e.response.text[:500]}")
        except Exception as e:
            raise HTTPException(500, f"Agent call failed: {str(e)}")
 
# ═══ PROPOSALS CRUD ═══
@app.get("/api/proposals")
async def list_proposals(_=Depends(verify_token)):
    with get_db() as db:
        rows = db.execute("SELECT * FROM proposals ORDER BY created_at DESC").fetchall()
        result = []
        for row in rows:
            p = dict(row)
            p["confidence"] = json.loads(p.pop("confidence_json") or "null")
            versions = db.execute(
                "SELECT label, text, is_current, created_at FROM versions WHERE proposal_id=? ORDER BY id",
                (p["id"],)
            ).fetchall()
            p["versions"] = [{"label": v["label"], "text": v["text"], "current": bool(v["is_current"]), "ts": v["created_at"]} for v in versions]
            result.append(p)
    return result
 
@app.post("/api/proposals")
async def create_proposal(req: ProposalCreate, _=Depends(verify_token)):
    with get_db() as db:
        db.execute(
            "INSERT INTO proposals (id, client, amount, date, status, text, saved_text, notes, followup, confidence_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (req.id, req.client, req.amount, req.date, req.status, req.text, req.text, req.notes, req.followup, json.dumps(req.confidence))
        )
        if req.versions:
            for v in req.versions:
                db.execute(
                    "INSERT INTO versions (proposal_id, label, text, is_current) VALUES (?,?,?,?)",
                    (req.id, v.get("label","v1"), v.get("text",""), 1 if v.get("current") else 0)
                )
        else:
            db.execute("INSERT INTO versions (proposal_id, label, text, is_current) VALUES (?,?,?,1)", (req.id, "v1 — AI Draft", req.text))
    return {"status": "created", "id": req.id}
 
@app.patch("/api/proposals/{proposal_id}")
async def update_proposal(proposal_id: str, req: ProposalUpdate, _=Depends(verify_token)):
    with get_db() as db:
        updates, params = [], []
        if req.status is not None:
            updates.append("status=?"); params.append(req.status)
        if req.text is not None:
            updates.append("text=?"); params.append(req.text)
            updates.append("saved_text=?"); params.append(req.text)
        if req.notes is not None:
            updates.append("notes=?"); params.append(req.notes)
        if req.followup is not None:
            updates.append("followup=?"); params.append(req.followup)
        if updates:
            updates.append("updated_at=?"); params.append(datetime.now(timezone.utc).isoformat())
            params.append(proposal_id)
            db.execute(f"UPDATE proposals SET {','.join(updates)} WHERE id=?", params)
    return {"status": "updated"}
 
@app.delete("/api/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str, _=Depends(verify_token)):
    with get_db() as db:
        db.execute("DELETE FROM proposals WHERE id=?", (proposal_id,))
    return {"status": "deleted"}
 
# ═══ EDIT LOG (RLHF Signal) ═══
@app.post("/api/edit-log")
async def log_edit(entry: EditLogEntry, _=Depends(verify_token)):
    with get_db() as db:
        db.execute(
            "INSERT INTO edit_log (proposal_id, agent, original_text, edited_text, deal_outcome) VALUES (?,?,?,?,?)",
            (entry.proposal_id, entry.agent, entry.original_text, entry.edited_text, entry.deal_outcome)
        )
    return {"status": "logged"}
 
@app.get("/api/edit-log")
async def get_edit_logs(_=Depends(verify_token)):
    with get_db() as db:
        rows = db.execute("SELECT * FROM edit_log ORDER BY created_at DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]
 
@app.get("/api/edit-log/stats")
async def edit_log_stats(_=Depends(verify_token)):
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) as c FROM edit_log").fetchone()["c"]
        by_agent = db.execute("SELECT agent, COUNT(*) as c FROM edit_log GROUP BY agent").fetchall()
        by_outcome = db.execute("SELECT deal_outcome, COUNT(*) as c FROM edit_log WHERE deal_outcome IS NOT NULL GROUP BY deal_outcome").fetchall()
    return {"total_edits": total, "by_agent": {r["agent"]: r["c"] for r in by_agent}, "by_outcome": {r["deal_outcome"]: r["c"] for r in by_outcome}}
 
# ═══ INVENTORY API ═══
@app.get("/api/inventory")
async def get_inventory(_=Depends(verify_token)):
    with get_db() as db:
        rows = db.execute("SELECT * FROM inventory ORDER BY price").fetchall()
    return [dict(r) for r in rows]
 
@app.put("/api/inventory/{sku}")
async def upsert_inventory(sku: str, item: InventoryItem, _=Depends(verify_token)):
    with get_db() as db:
        db.execute("""
            INSERT INTO inventory (sku, name, gpu, gpu_mem, vram, price, stock, rack_u, power, nvlink, fp16, colo, arch, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(sku) DO UPDATE SET
                name=excluded.name, gpu=excluded.gpu, gpu_mem=excluded.gpu_mem, vram=excluded.vram,
                price=excluded.price, stock=excluded.stock, rack_u=excluded.rack_u, power=excluded.power,
                nvlink=excluded.nvlink, fp16=excluded.fp16, colo=excluded.colo, arch=excluded.arch,
                updated_at=excluded.updated_at
        """, (sku, item.name, item.gpu, item.gpu_mem, item.vram, item.price, item.stock, item.rack_u, item.power, item.nvlink, item.fp16, item.colo, item.arch, datetime.now(timezone.utc).isoformat()))
    return {"status": "upserted", "sku": sku}
 
@app.post("/api/inventory/seed")
async def seed_inventory(_=Depends(verify_token)):
    """Seed the inventory table from the hardcoded INVENTORY in the frontend."""
    default_inventory = [
        {"sku":"4090-8x","name":"RTX 4090 8× Cluster","gpu":"RTX 4090","gpu_mem":24,"vram":192,"price":28000,"stock":12,"rack_u":4,"power":3.2,"nvlink":"PCIe bridge pairs","fp16":660.8,"colo":1120,"arch":"passthrough"},
        {"sku":"5090-8x","name":"RTX 5090 8× Cluster","gpu":"RTX 5090","gpu_mem":32,"vram":256,"price":52000,"stock":3,"rack_u":4,"power":4.8,"nvlink":"NVLink 5.0 full mesh","fp16":838.4,"colo":2150,"arch":"nvlink"},
        {"sku":"4090-4x","name":"RTX 4090 4× Node","gpu":"RTX 4090","gpu_mem":24,"vram":96,"price":15500,"stock":8,"rack_u":2,"power":1.6,"nvlink":"PCIe bridge pairs","fp16":330.4,"colo":720,"arch":"passthrough"},
        {"sku":"5090-4x","name":"RTX 5090 4× Node","gpu":"RTX 5090","gpu_mem":32,"vram":128,"price":28000,"stock":0,"rack_u":2,"power":2.4,"nvlink":"NVLink 5.0 full mesh","fp16":419.2,"colo":1080,"arch":"nvlink"},
        {"sku":"A100-8x","name":"A100-80G 8× Server","gpu":"A100-80G SXM","gpu_mem":80,"vram":640,"price":180000,"stock":1,"rack_u":8,"power":6.4,"nvlink":"NVSwitch full fabric","fp16":624,"colo":2870,"arch":"nvswitch"},
        {"sku":"PRO6000-8x-PT","name":"RTX Pro 6000 SE 8× Server (Passthrough)","gpu":"RTX Pro 6000 SE","gpu_mem":96,"vram":768,"price":128014,"stock":16,"rack_u":7,"power":5.0,"nvlink":"PCIe Gen5 via CPU root complex","fp16":792,"colo":2240,"arch":"passthrough"},
        {"sku":"PRO6000-8x-CX8","name":"RTX Pro 6000 SE 8× Server (MGX CX8)","gpu":"RTX Pro 6000 SE","gpu_mem":96,"vram":768,"price":200000,"stock":0,"rack_u":4,"power":5.0,"nvlink":"4× CX8 SuperNIC 800GbE","fp16":792,"colo":2290,"arch":"cx8"},
        {"sku":"H100-8x","name":"H100 SXM5 8× Node (DGX-class)","gpu":"H100 SXM5","gpu_mem":80,"vram":640,"price":280000,"stock":0,"rack_u":8,"power":10.2,"nvlink":"NVSwitch 4th-gen","fp16":3958,"colo":4570,"arch":"nvswitch"},
    ]
    with get_db() as db:
        for item in default_inventory:
            db.execute("""
                INSERT OR REPLACE INTO inventory (sku, name, gpu, gpu_mem, vram, price, stock, rack_u, power, nvlink, fp16, colo, arch, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (item["sku"], item["name"], item["gpu"], item["gpu_mem"], item["vram"], item["price"], item["stock"], item["rack_u"], item["power"], item["nvlink"], item["fp16"], item["colo"], item["arch"], datetime.now(timezone.utc).isoformat()))
    return {"status": "seeded", "count": len(default_inventory)}
 
# ═══ DEAL INTELLIGENCE ═══
 
# ═══ FLEET INVENTORY ═══
class FleetServer(BaseModel):
    label: str = ""
    model: str = ""
    dc: str = ""
    rack: str = ""
    status: str = "Rental"
    assigned_to: str = ""
    cpu: str = ""
    memory: str = ""
    ip: str = ""
    os: str = ""
    notes: str = ""
 
@app.get("/api/fleet")
async def list_fleet(_=Depends(verify_token)):
    with get_db() as db:
        rows = db.execute("SELECT * FROM fleet_servers ORDER BY dc, model, label").fetchall()
    return [dict(r) for r in rows]
 
@app.get("/api/fleet/summary")
async def fleet_summary(_=Depends(verify_token)):
    """Summary for Architect Agent — models, availability, DCs."""
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) as c FROM fleet_servers").fetchone()["c"]
        available = db.execute("SELECT COUNT(*) as c FROM fleet_servers WHERE assigned_to IS NULL OR assigned_to = ''").fetchone()["c"]
        by_model = db.execute("""
            SELECT model, dc, status,
                COUNT(*) as total,
                SUM(CASE WHEN assigned_to IS NULL OR assigned_to = '' THEN 1 ELSE 0 END) as available
            FROM fleet_servers GROUP BY model, dc, status ORDER BY model, dc
        """).fetchall()
        by_dc = db.execute("""
            SELECT dc, COUNT(*) as total,
                SUM(CASE WHEN assigned_to IS NULL OR assigned_to = '' THEN 1 ELSE 0 END) as available
            FROM fleet_servers GROUP BY dc ORDER BY dc
        """).fetchall()
    return {
        "total": total, "available": available, "assigned": total - available,
        "by_model": [dict(r) for r in by_model],
        "by_dc": [dict(r) for r in by_dc]
    }
 
@app.post("/api/fleet/import")
async def import_fleet(servers: list[dict], _=Depends(verify_token)):
    """Bulk import fleet servers (from Excel upload on frontend)."""
    imported = 0
    with get_db() as db:
        for s in servers:
            label = s.get("label", "")
            if not label:
                continue
            db.execute("""
                INSERT INTO fleet_servers (label, model, dc, rack, status, assigned_to, cpu, memory, ip, os, notes, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(label) DO UPDATE SET
                    model=excluded.model, dc=excluded.dc, rack=excluded.rack,
                    status=excluded.status, assigned_to=excluded.assigned_to,
                    cpu=excluded.cpu, memory=excluded.memory, ip=excluded.ip,
                    os=excluded.os, notes=excluded.notes, updated_at=excluded.updated_at
            """, (label, s.get("model",""), s.get("dc",""), s.get("rack",""),
                  s.get("status","Rental"), s.get("assignedTo",""),
                  s.get("cpu",""), s.get("memory",""), s.get("ip",""),
                  s.get("os",""), s.get("notes",""),
                  datetime.now(timezone.utc).isoformat()))
            imported += 1
    return {"status": "imported", "count": imported}
 
@app.patch("/api/fleet/{server_id}")
async def update_fleet_server(server_id: int, updates: dict, _=Depends(verify_token)):
    allowed = {"label","model","dc","rack","status","assigned_to","cpu","memory","ip","os","notes"}
    with get_db() as db:
        sets, params = [], []
        for k, v in updates.items():
            if k in allowed:
                sets.append(f"{k}=?"); params.append(v)
        if sets:
            sets.append("updated_at=?"); params.append(datetime.now(timezone.utc).isoformat())
            params.append(server_id)
            db.execute(f"UPDATE fleet_servers SET {','.join(sets)} WHERE id=?", params)
    return {"status": "updated"}
 
# ═══ DEAL INTELLIGENCE ═══
@app.get("/api/deal-intel")
async def deal_intelligence(_=Depends(verify_token)):
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) as c FROM proposals").fetchone()["c"]
        won = db.execute("SELECT COUNT(*) as c FROM proposals WHERE status='success'").fetchone()["c"]
        lost = db.execute("SELECT COUNT(*) as c FROM proposals WHERE status='lost'").fetchone()["c"]
        pending = db.execute("SELECT COUNT(*) as c FROM proposals WHERE status='pending'").fetchone()["c"]
        # Average won deal
        avg_won = db.execute("SELECT AVG(CAST(REPLACE(REPLACE(amount,'$',''),',','') AS REAL)) as avg FROM proposals WHERE status='success' AND amount IS NOT NULL AND amount != 'N/A'").fetchone()["avg"]
        # Pipeline value
        pipeline = db.execute("SELECT SUM(CAST(REPLACE(REPLACE(amount,'$',''),',','') AS REAL)) as total FROM proposals WHERE status='pending' AND amount IS NOT NULL AND amount != 'N/A'").fetchone()["total"]
        # Overdue followups
        overdue = db.execute("SELECT COUNT(*) as c FROM proposals WHERE status='pending' AND followup IS NOT NULL AND followup < date('now')").fetchone()["c"]
        # RLHF readiness
        edit_count = db.execute("SELECT COUNT(*) as c FROM edit_log").fetchone()["c"]
    closed = won + lost
    return {
        "total": total, "won": won, "lost": lost, "pending": pending,
        "win_rate": f"{round(won/closed*100)}%" if closed > 0 else "—",
        "avg_won_deal": f"${round(avg_won):,}" if avg_won else "—",
        "pipeline_value": f"${round(pipeline):,}" if pipeline else "$0",
        "overdue_followups": overdue,
        "rlhf_edits": edit_count,
        "rlhf_ready": edit_count >= 20
    }
 
# ═══ HEALTH ═══
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "api_key_configured": bool(ANTHROPIC_API_KEY),
        "db_exists": DB_PATH.exists(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
 
# ═══ GOOGLE SHEETS INVENTORY SYNC ═══
# Set SHEETS_API_KEY and SHEETS_ID env vars to enable
SHEETS_API_KEY = os.getenv("SHEETS_API_KEY", "")
SHEETS_ID = os.getenv("SHEETS_ID", "")  # Google Sheets spreadsheet ID
SHEETS_RANGE = os.getenv("SHEETS_RANGE", "Inventory!A2:M")  # Sheet tab + range
 
@app.post("/api/inventory/sync-sheets")
async def sync_from_sheets(_=Depends(verify_token)):
    """Pull latest inventory from a Google Sheet and upsert into DB.
    
    Expected Sheet columns (A-M):
    SKU | Name | GPU | GPU Mem | VRAM | Price | Stock | Rack U | Power | NVLink | FP16 | Colo | Arch
    """
    if not SHEETS_API_KEY or not SHEETS_ID:
        raise HTTPException(400, "Google Sheets not configured. Set SHEETS_API_KEY and SHEETS_ID env vars.")
    
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEETS_ID}/values/{SHEETS_RANGE}?key={SHEETS_API_KEY}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise HTTPException(500, f"Sheets API error: {str(e)}")
    
    rows = data.get("values", [])
    if not rows:
        return {"status": "no_data", "count": 0}
    
    updated = 0
    with get_db() as db:
        for row in rows:
            if len(row) < 13:
                continue
            try:
                sku, name, gpu, gpu_mem, vram, price, stock, rack_u, power, nvlink, fp16, colo, arch = row[:13]
                db.execute("""
                    INSERT INTO inventory (sku, name, gpu, gpu_mem, vram, price, stock, rack_u, power, nvlink, fp16, colo, arch, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(sku) DO UPDATE SET
                        name=excluded.name, stock=excluded.stock, price=excluded.price,
                        gpu=excluded.gpu, gpu_mem=excluded.gpu_mem, vram=excluded.vram,
                        rack_u=excluded.rack_u, power=excluded.power, nvlink=excluded.nvlink,
                        fp16=excluded.fp16, colo=excluded.colo, arch=excluded.arch,
                        updated_at=excluded.updated_at
                """, (sku, name, gpu, int(gpu_mem), int(vram), float(price), int(stock),
                      int(rack_u), float(power), nvlink, float(fp16), float(colo), arch,
                      datetime.now(timezone.utc).isoformat()))
                updated += 1
            except (ValueError, IndexError) as e:
                continue  # Skip malformed rows
    
    return {"status": "synced", "rows_updated": updated}
 
@app.get("/api/inventory/freshness")
async def inventory_freshness(_=Depends(verify_token)):
    """Check when inventory was last updated."""
    with get_db() as db:
        row = db.execute("SELECT MAX(updated_at) as latest FROM inventory").fetchone()
        count = db.execute("SELECT COUNT(*) as c FROM inventory").fetchone()["c"]
        oos = db.execute("SELECT COUNT(*) as c FROM inventory WHERE stock=0").fetchone()["c"]
    return {
        "last_updated": row["latest"] if row else None,
        "total_skus": count,
        "out_of_stock": oos,
        "sheets_configured": bool(SHEETS_API_KEY and SHEETS_ID)
    }
 
# ═══ STARTUP ═══
@app.on_event("startup")
async def startup():
    init_db()
    # Auto-seed inventory if empty
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) as c FROM inventory").fetchone()["c"]
        if count == 0:
            await seed_inventory()
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
