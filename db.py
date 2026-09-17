import os
from contextlib import contextmanager

try:
    import psycopg
except ImportError:
    psycopg = None

SCHEMA_STATEMENTS = [
"CREATE TABLE IF NOT EXISTS leads (id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL, location TEXT NOT NULL, signal TEXT NOT NULL, score INTEGER NOT NULL DEFAULT 0, stage TEXT NOT NULL DEFAULT 'New', website TEXT, source TEXT NOT NULL DEFAULT 'manual', metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
"CREATE INDEX IF NOT EXISTS leads_stage_idx ON leads(stage)",
"CREATE INDEX IF NOT EXISTS leads_score_idx ON leads(score DESC)",
"CREATE TABLE IF NOT EXISTS activities (id BIGSERIAL PRIMARY KEY, kind TEXT NOT NULL, message TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
"CREATE INDEX IF NOT EXISTS activities_created_idx ON activities(created_at DESC)",
"CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
]


def database_url(): return os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
def configured(): return bool(database_url() and psycopg)

def require_database():
    if not database_url(): raise RuntimeError("DATABASE_URL is not configured. Connect PostgreSQL through Vercel before using persistent features.")
    if psycopg is None: raise RuntimeError("psycopg is not installed.")

@contextmanager
def connection():
    require_database(); conn=psycopg.connect(database_url(), connect_timeout=8)
    try: yield conn; conn.commit()
    except Exception: conn.rollback(); raise
    finally: conn.close()

def ensure_schema():
    with connection() as conn:
        for statement in SCHEMA_STATEMENTS: conn.execute(statement)
        for key,value in {"workspace":"ClientGrowth AI Command Center","service":"Websites · Automation · Digital Systems"}.items():
            conn.execute("INSERT INTO settings(key,value) VALUES(%s,%s) ON CONFLICT(key) DO NOTHING",(key,value))

def list_leads():
    ensure_schema()
    with connection() as conn:
        rows=conn.execute("SELECT id,name,type,location,signal,score,stage,website,source,created_at,updated_at FROM leads ORDER BY score DESC,created_at DESC").fetchall()
        cols=["id","name","type","location","signal","score","stage","website","source","created_at","updated_at"]
        return [dict(zip(cols,row)) for row in rows]

def create_lead(data):
    ensure_schema()
    with connection() as conn:
        row=conn.execute("INSERT INTO leads(name,type,location,signal,score,stage,website,source,metadata) VALUES(%s,%s,%s,%s,%s,'New',%s,%s,%s) RETURNING id,name,type,location,signal,score,stage,website,source,created_at,updated_at",(data["name"],data["type"],data["location"],data["signal"],data.get("score",0),data.get("website"),data.get("source","manual"),data.get("metadata",{}))).fetchone()
        cols=["id","name","type","location","signal","score","stage","website","source","created_at","updated_at"]
        return dict(zip(cols,row))

def update_stage(lead_id,stage):
    ensure_schema()
    with connection() as conn:
        row=conn.execute("UPDATE leads SET stage=%s,updated_at=NOW() WHERE id=%s RETURNING id,name,type,location,signal,score,stage,website,source,created_at,updated_at",(stage,lead_id)).fetchone()
        if not row: return None
        cols=["id","name","type","location","signal","score","stage","website","source","created_at","updated_at"]
        return dict(zip(cols,row))

def add_activity(kind,message):
    ensure_schema()
    with connection() as conn: conn.execute("INSERT INTO activities(kind,message) VALUES(%s,%s)",(kind,message))

def recent_activities(limit=20):
    ensure_schema()
    with connection() as conn:
        rows=conn.execute("SELECT kind,message,created_at FROM activities ORDER BY created_at DESC LIMIT %s",(limit,)).fetchall()
        return [(r[0],r[1],r[2].strftime("%Y-%m-%d %H:%M UTC")) for r in rows]

def get_settings():
    ensure_schema()
    with connection() as conn: return {r[0]:r[1] for r in conn.execute("SELECT key,value FROM settings").fetchall()}

def save_settings(workspace,service):
    ensure_schema()
    with connection() as conn:
        conn.execute("INSERT INTO settings(key,value,updated_at) VALUES('workspace',%s,NOW()) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value,updated_at=NOW()",(workspace,))
        conn.execute("INSERT INTO settings(key,value,updated_at) VALUES('service',%s,NOW()) ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value,updated_at=NOW()",(service,))

def counts():
    ensure_schema()
    with connection() as conn:
        return {"leads":conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0],"qualified":conn.execute("SELECT COUNT(*) FROM leads WHERE stage IN ('Qualified','Contacted','Replied')").fetchone()[0],"opportunities":conn.execute("SELECT COUNT(*) FROM leads WHERE stage<>'New'").fetchone()[0]}

def db_status():
    try: ensure_schema(); return {"configured":True,"connected":True}
    except Exception as exc: return {"configured":bool(database_url()),"connected":False,"error":str(exc)}
