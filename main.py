import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db import configured, db_status, list_leads, create_lead, update_stage, add_activity, recent_activities, get_settings, save_settings, counts
from engines import website_audit, google_places_search, openai_generate
from intelligence import classify_prospect, whatsapp_link, campaign_guard

BASE = Path(__file__).parent
app = FastAPI(title="ClientGrowth AI Command Center", version="2.1.1")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")
stages = ["New", "Qualified", "Contacted", "Replied"]

FAVICON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="#0b1020"/><path d="M18 20h10v9h18v-9h10v24H46v-9H28v9H18z" fill="#ffffff"/><circle cx="32" cy="12" r="3" fill="#7c5cff"/></svg>'''


@app.get("/favicon.ico")
def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=31536000, immutable"})


def integration_state():
    return {
        "database": configured(),
        "openai": bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL")),
        "maps": bool(os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_PLACES_API_KEY")),
        "linkedin": bool(os.getenv("LINKEDIN_ACCESS_TOKEN")),
        "email_sender": bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD")),
        "whatsapp_business": bool(os.getenv("WHATSAPP_ACCESS_TOKEN") and os.getenv("WHATSAPP_PHONE_NUMBER_ID")),
    }


def context(request, active, **extra):
    try:
        leads = list_leads(); settings = get_settings(); activities = recent_activities(); db_error = None
    except Exception as exc:
        leads, activities = [], []
        settings = {"workspace":"ClientGrowth AI Command Center", "service":"Websites · Automation · Digital Systems"}
        db_error = str(exc)
    data = {"request":request,"active":active,"leads":leads,"activities":activities,"settings":settings,"integrations":integration_state(),"db_error":db_error}
    data.update(extra)
    return data


def require_db():
    if not configured(): raise HTTPException(503, "Persistent storage is not configured. Connect PostgreSQL and set DATABASE_URL.")


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    try: stats = counts()
    except Exception: stats = {"leads":0,"qualified":0,"opportunities":0}
    return templates.TemplateResponse("dashboard.html", context(request,"dashboard",stats=stats))

@app.get("/radar", response_class=HTMLResponse)
def radar(request: Request, q: str = "", signal: str = "all"):
    visible = list_leads() if configured() else []
    qv=q.strip().lower()
    if qv: visible=[x for x in visible if qv in f"{x['name']} {x['type']} {x['location']} {x['signal']}".lower()]
    if signal == "high": visible=[x for x in visible if x["score"] >= 85]
    if signal == "new": visible=[x for x in visible if x["stage"] == "New"]
    return templates.TemplateResponse("radar.html", context(request,"radar",leads=visible,query=q,signal=signal))

@app.post("/radar/add", response_class=HTMLResponse)
def add_lead(request: Request, name: str=Form(...), lead_type: str=Form(...), location: str=Form(...), signal: str=Form(...), website: str=Form("")):
    require_db(); lead=create_lead({"name":name.strip(),"type":lead_type.strip(),"location":location.strip(),"signal":signal.strip(),"website":website.strip() or None,"score":0,"source":"manual"}); add_activity("Lead Radar",f"Added {lead['name']} manually"); return radar(request)

@app.get("/maps", response_class=HTMLResponse)
def maps(request: Request): return templates.TemplateResponse("maps.html", context(request,"maps",results=[]))

@app.post("/maps", response_class=HTMLResponse)
def maps_search(request: Request, query: str=Form(...), location: str=Form("")):
    try: results=google_places_search(query,location); error=None
    except Exception as exc: results=[]; error=str(exc)
    enriched=[]
    for result in results: enriched.append({**result,"qualification":classify_prospect(result),"whatsapp_link":whatsapp_link(result.get("phone"))})
    return templates.TemplateResponse("maps.html", context(request,"maps",results=enriched,query=query,location=location,error=error))

@app.post("/maps/import", response_class=HTMLResponse)
def maps_import(request: Request, name: str=Form(...), lead_type: str=Form("Business"), location: str=Form(...), website: str=Form(""), phone: str=Form(""), maps_url: str=Form("")):
    require_db(); q=classify_prospect({"website":website,"phone":phone}); lead=create_lead({"name":name,"type":lead_type,"location":location,"signal":f"{q['priority']} priority · {q['website_status']}","website":website or maps_url,"score":q["score"],"source":"google-places","metadata":{"phone":phone,"maps_url":maps_url,"qualification":q}}); add_activity("Lead Radar",f"Imported and qualified {lead['name']} from Google Places"); return templates.TemplateResponse("maps.html", context(request,"maps",results=[],notice=f"{lead['name']} was saved and qualified as {q['priority']} priority."))
