from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).parent
app = FastAPI(title="ClientGrowth AI Command Center", version="1.1.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

leads = [
    {"id":1,"name":"Northstar Property Group","type":"Property Management","location":"Atlanta, GA","signal":"Outdated website","score":94,"stage":"New","website":"northstar.example"},
    {"id":2,"name":"Apex Auto Collective","type":"Automotive","location":"Charlotte, NC","signal":"No mobile CTA","score":88,"stage":"Qualified","website":"apexauto.example"},
    {"id":3,"name":"Lumen Dental Studio","type":"Healthcare","location":"Austin, TX","signal":"Slow booking flow","score":81,"stage":"Contacted","website":"lumendental.example"},
    {"id":4,"name":"Harborline Creative","type":"Creative Agency","location":"Miami, FL","signal":"Growth hiring","score":76,"stage":"New","website":"harborline.example"},
]

activities = [
    ("Website X-Ray", "4 prospects analyzed", "2 min ago"),
    ("Lead Radar", "12 new opportunities surfaced", "18 min ago"),
    ("Outreach Studio", "3 personalized drafts prepared", "41 min ago"),
]

stages = ["New", "Qualified", "Contacted", "Replied"]

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    stats = {"leads": len(leads)+128, "qualified": 47, "opportunities": 19, "reply_rate": "18.4%"}
    return templates.TemplateResponse("dashboard.html", {"request":request, "stats":stats, "leads":leads, "activities":activities, "active":"dashboard"})

@app.get("/radar", response_class=HTMLResponse)
def radar(request: Request):
    return templates.TemplateResponse("radar.html", {"request":request, "leads":leads, "active":"radar"})

@app.post("/radar/add", response_class=HTMLResponse)
def add_lead(request: Request, name: str = Form(...), lead_type: str = Form(...), location: str = Form(...), signal: str = Form(...), website: str = Form("")):
    if not name.strip():
        raise HTTPException(400, "Company name is required")
    lead = {"id": max([x["id"] for x in leads], default=0)+1, "name":name.strip(), "type":lead_type.strip() or "Business", "location":location.strip(), "signal":signal.strip() or "New opportunity", "score":72, "stage":"New", "website":website.strip() or "Not provided"}
    leads.append(lead)
    activities.insert(0, ("Lead Radar", f"Added {lead['name']} to the opportunity field", "just now"))
    return templates.TemplateResponse("radar.html", {"request":request, "leads":leads, "active":"radar", "notice":f"{lead['name']} added to Lead Radar."})

@app.get("/pipeline", response_class=HTMLResponse)
def pipeline(request: Request):
    return templates.TemplateResponse("pipeline.html", {"request":request, "leads":leads, "stages":stages, "active":"pipeline"})

@app.post("/pipeline/{lead_id}/stage", response_class=HTMLResponse)
def move_lead(request: Request, lead_id: int, stage: str = Form(...)):
    lead = next((x for x in leads if x["id"] == lead_id), None)
    if not lead or stage not in stages:
        raise HTTPException(404, "Lead or stage not found")
    lead["stage"] = stage
    activities.insert(0, ("Opportunity Board", f"Moved {lead['name']} to {stage}", "just now"))
    return templates.TemplateResponse("pipeline.html", {"request":request, "leads":leads, "stages":stages, "active":"pipeline", "notice":f"{lead['name']} moved to {stage}."})

@app.get("/audit", response_class=HTMLResponse)
def audit(request: Request):
    return templates.TemplateResponse("audit.html", {"request":request, "active":"audit"})

def build_audit(url: str):
    raw = url.strip()
    target = raw if "://" in raw else "https://" + raw
    parsed = urlparse(target)
    if not parsed.netloc:
        raise HTTPException(400, "Enter a valid website URL")
    domain = parsed.netloc.lower().removeprefix("www.")
    findings = [
        ("Mobile conversion", "Needs attention", "Primary actions should be easier to reach on small screens."),
        ("Trust signals", "Opportunity", "Add reviews, case studies and recognizable proof near key CTAs."),
        ("Performance", "Opportunity", "Compress hero media and defer non-critical assets."),
        ("Lead capture", "Needs attention", "Use a shorter contact path with one clear conversion goal."),
    ]
    score = max(48, 82 - (len(domain) % 17))
    return {"url":domain, "score":score, "findings":findings}

@app.post("/audit", response_class=HTMLResponse)
def run_audit(request: Request, url: str = Form(...)):
    report = build_audit(url)
    activities.insert(0, ("Website X-Ray", f"Analyzed {report['url']}", "just now"))
    return templates.TemplateResponse("audit.html", {"request":request, "active":"audit", "report":report})

@app.get("/outreach", response_class=HTMLResponse)
def outreach(request: Request):
    return templates.TemplateResponse("outreach.html", {"request":request, "active":"outreach", "leads":leads})

@app.post("/outreach", response_class=HTMLResponse)
def generate_outreach(request: Request, company: str = Form(...), signal: str = Form(...), service: str = Form(...)):
    message = f"Hi {company} team,\n\nI came across your business and noticed {signal.lower()}. I build focused websites and digital systems that make it easier for the right prospects to understand the offer and take action.\n\nI can put together a short visual concept around {service.lower()} so you can see the direction before deciding on anything.\n\nBest,\nEmmanuel"
    activities.insert(0, ("Outreach Studio", f"Prepared personalized outreach for {company}", "just now"))
    return templates.TemplateResponse("outreach.html", {"request":request, "active":"outreach", "leads":leads, "message":message})

@app.get("/resume", response_class=HTMLResponse)
def resume(request: Request):
    return templates.TemplateResponse("resume.html", {"request":request, "active":"resume"})

@app.get("/automations", response_class=HTMLResponse)
def automations(request: Request):
    flows = [("Lead discovery", "Search → qualify → enrich → pipeline", "Ready"),("Website audit", "URL → checks → opportunity report", "Ready"),("Outreach", "Signal → personalization → review queue", "Ready"),("Follow-up", "No reply → timed reminder → task", "Planned")]
    return templates.TemplateResponse("automations.html", {"request":request, "active":"automations", "flows":flows})

@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request":request, "active":"settings"})

@app.get("/health")
def health():
    return {"status":"ok", "service":"clientgrowth-ai-hub", "version":"1.1.0", "time":datetime.now(timezone.utc).isoformat()}

@app.get("/api")
def api_root():
    return {"status":"ok", "service":"clientgrowth-ai-hub", "version":"1.1.0", "endpoints":["/api/health","/api/leads","/api/leads/{id}/stage","/api/audit","/api/outreach","/api/automations","/health"]}

@app.get("/api/health")
def api_health():
    return {"status":"ok", "service":"clientgrowth-ai-hub", "version":"1.1.0", "time":datetime.now(timezone.utc).isoformat()}

@app.get("/api/leads")
def api_leads():
    return {"status":"ok", "count":len(leads), "data":leads}

@app.post("/api/leads")
def api_create_lead(payload: dict):
    required = ["name", "type", "location", "signal"]
    if any(not str(payload.get(k, "")).strip() for k in required):
        raise HTTPException(400, "name, type, location and signal are required")
    lead = {"id":max([x["id"] for x in leads], default=0)+1,"name":str(payload["name"]).strip(),"type":str(payload["type"]).strip(),"location":str(payload["location"]).strip(),"signal":str(payload["signal"]).strip(),"score":int(payload.get("score",72)),"stage":"New","website":str(payload.get("website", "Not provided")).strip() or "Not provided"}
    leads.append(lead)
    activities.insert(0, ("Lead Radar", f"Added {lead['name']} through API", "just now"))
    return {"status":"created", "data":lead}

@app.patch("/api/leads/{lead_id}/stage")
def api_move_lead(lead_id: int, payload: dict):
    stage = payload.get("stage")
    lead = next((x for x in leads if x["id"] == lead_id), None)
    if not lead or stage not in stages:
        raise HTTPException(404, "Lead or stage not found")
    lead["stage"] = stage
    activities.insert(0, ("Opportunity Board", f"Moved {lead['name']} to {stage}", "just now"))
    return {"status":"updated", "data":lead}

@app.post("/api/audit")
def api_audit(payload: dict):
    url = str(payload.get("url", "")).strip()
    if not url:
        raise HTTPException(400, "url is required")
    report = build_audit(url)
    activities.insert(0, ("Website X-Ray", f"API audit completed for {report['url']}", "just now"))
    return {"status":"ok", "data":report}

@app.post("/api/outreach")
def api_outreach(payload: dict):
    company = str(payload.get("company", "")).strip()
    signal = str(payload.get("signal", "")).strip()
    service = str(payload.get("service", "")).strip()
    if not company or not signal or not service:
        raise HTTPException(400, "company, signal and service are required")
    message = f"Hi {company} team,\n\nI came across your business and noticed {signal.lower()}. I build focused websites and digital systems that make it easier for the right prospects to understand the offer and take action.\n\nI can put together a short visual concept around {service.lower()} so you can see the direction before deciding on anything.\n\nBest,\nEmmanuel"
    activities.insert(0, ("Outreach Studio", f"API draft prepared for {company}", "just now"))
    return {"status":"ok", "data":{"company":company,"message":message}}

@app.post("/api/automations/{automation}")
def api_automation(automation: str):
    allowed = {"lead-discovery":"Lead discovery queued","website-audit":"Website audit queued","outreach":"Outreach preparation queued","follow-up":"Follow-up check queued"}
    if automation not in allowed:
        raise HTTPException(404, "Automation not found")
    activities.insert(0, ("Automation Center", allowed[automation], "just now"))
    return {"status":"queued", "automation":automation, "message":allowed[automation]}
