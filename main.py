from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).parent
app = FastAPI(title="ClientGrowth AI Command Center", version="1.2.0")
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
settings_state = {
    "workspace": "ClientGrowth AI Command Center",
    "service": "Websites · Automation · Digital Systems",
    "openai": False,
    "maps": False,
    "linkedin": False,
}


def page_context(request: Request, active: str, **extra):
    context = {"request": request, "active": active, "leads": leads, "settings": settings_state}
    context.update(extra)
    return context


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    stats = {"leads": len(leads)+128, "qualified": sum(1 for x in leads if x["stage"] in {"Qualified", "Contacted", "Replied"}) + 43, "opportunities": sum(1 for x in leads if x["stage"] != "New") + 15, "reply_rate": "18.4%"}
    return templates.TemplateResponse("dashboard.html", page_context(request, "dashboard", stats=stats, activities=activities))


@app.get("/radar", response_class=HTMLResponse)
def radar(request: Request, q: str = "", signal: str = "all"):
    q_clean = q.strip().lower()
    visible = [x for x in leads if (not q_clean or q_clean in f"{x['name']} {x['type']} {x['location']} {x['signal']}".lower())]
    if signal == "high":
        visible = [x for x in visible if x["score"] >= 85]
    elif signal == "new":
        visible = [x for x in visible if x["stage"] == "New"]
    return templates.TemplateResponse("radar.html", page_context(request, "radar", leads=visible, query=q, signal=signal))


@app.post("/radar/add", response_class=HTMLResponse)
def add_lead(request: Request, name: str = Form(...), lead_type: str = Form(...), location: str = Form(...), signal: str = Form(...), website: str = Form("")):
    if not name.strip():
        raise HTTPException(400, "Company name is required")
    lead = {"id": max([x["id"] for x in leads], default=0)+1, "name":name.strip(), "type":lead_type.strip() or "Business", "location":location.strip(), "signal":signal.strip() or "New opportunity", "score":72, "stage":"New", "website":website.strip() or "Not provided"}
    leads.append(lead)
    activities.insert(0, ("Lead Radar", f"Added {lead['name']} to the opportunity field", "just now"))
    return radar(request, q="", signal="all")


@app.get("/pipeline", response_class=HTMLResponse)
def pipeline(request: Request):
    return templates.TemplateResponse("pipeline.html", page_context(request, "pipeline", stages=stages))


@app.post("/pipeline/{lead_id}/stage", response_class=HTMLResponse)
def move_lead(request: Request, lead_id: int, stage: str = Form(...)):
    lead = next((x for x in leads if x["id"] == lead_id), None)
    if not lead or stage not in stages:
        raise HTTPException(404, "Lead or stage not found")
    lead["stage"] = stage
    activities.insert(0, ("Opportunity Board", f"Moved {lead['name']} to {stage}", "just now"))
    return templates.TemplateResponse("pipeline.html", page_context(request, "pipeline", stages=stages, notice=f"{lead['name']} moved to {stage}."))


@app.get("/audit", response_class=HTMLResponse)
def audit(request: Request):
    return templates.TemplateResponse("audit.html", page_context(request, "audit"))


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
    return templates.TemplateResponse("audit.html", page_context(request, "audit", report=report))


@app.get("/outreach", response_class=HTMLResponse)
def outreach(request: Request):
    return templates.TemplateResponse("outreach.html", page_context(request, "outreach"))


@app.post("/outreach", response_class=HTMLResponse)
def generate_outreach(request: Request, company: str = Form(...), signal: str = Form(...), service: str = Form(...)):
    message = make_outreach(company, signal, service)
    activities.insert(0, ("Outreach Studio", f"Prepared personalized outreach for {company}", "just now"))
    return templates.TemplateResponse("outreach.html", page_context(request, "outreach", message=message))


def make_outreach(company: str, signal: str, service: str):
    return f"Hi {company} team,\n\nI came across your business and noticed {signal.lower()}. I build focused websites and digital systems that make it easier for the right prospects to understand the offer and take action.\n\nI can put together a short visual concept around {service.lower()} so you can see the direction before deciding on anything.\n\nBest,\nEmmanuel"


@app.get("/resume", response_class=HTMLResponse)
def resume(request: Request):
    return templates.TemplateResponse("resume.html", page_context(request, "resume"))


@app.post("/resume", response_class=HTMLResponse)
def resume_action(request: Request, mode: str = Form(...), target: str = Form("Web Developer"), job: str = Form("")):
    if mode == "resume":
        result = "Emmanuel — Web Developer & Digital Builder\n\nFocus: responsive business websites, e-commerce, automation and AI-powered digital systems.\n\nCore strengths: WordPress · WooCommerce · React · Python · FastAPI · AI Automation\n\nPositioning: I turn business requirements into practical, conversion-focused digital experiences."
    elif mode == "match":
        text = job.strip() or "No job description supplied."
        result = f"JOB MATCH REVIEW\n\nTarget: {target}\n\nInput reviewed: {text[:420]}\n\nSuggested evidence to emphasize: shipped websites, responsive UX, API integrations, automation workflows and measurable business outcomes."
    else:
        result = "PROFILE BUILDER\n\nHeadline: Web Developer & Digital Builder | Websites · Automation · AI\n\nAbout: I build modern business websites and practical digital systems that help companies present their services clearly, capture demand and automate repeatable work."
    return templates.TemplateResponse("resume.html", page_context(request, "resume", result=result))


@app.get("/automations", response_class=HTMLResponse)
def automations(request: Request):
    flows = [("Lead discovery", "Search → qualify → enrich → pipeline", "Ready", "lead-discovery"),("Website audit", "URL → checks → opportunity report", "Ready", "website-audit"),("Outreach", "Signal → personalization → review queue", "Ready", "outreach"),("Follow-up", "No reply → timed reminder → task", "Planned", "follow-up")]
    return templates.TemplateResponse("automations.html", page_context(request, "automations", flows=flows))


@app.post("/automations/run", response_class=HTMLResponse)
def run_automation(request: Request, automation: str = Form(...)):
    labels = {"lead-discovery":"Lead discovery queued","website-audit":"Website audit queued","outreach":"Outreach preparation queued","follow-up":"Follow-up check queued"}
    if automation not in labels:
        raise HTTPException(404, "Automation not found")
    activities.insert(0, ("Automation Center", labels[automation], "just now"))
    flows = [("Lead discovery", "Search → qualify → enrich → pipeline", "Queued" if automation=="lead-discovery" else "Ready", "lead-discovery"),("Website audit", "URL → checks → opportunity report", "Queued" if automation=="website-audit" else "Ready", "website-audit"),("Outreach", "Signal → personalization → review queue", "Queued" if automation=="outreach" else "Ready", "outreach"),("Follow-up", "No reply → timed reminder → task", "Queued" if automation=="follow-up" else "Planned", "follow-up")]
    return templates.TemplateResponse("automations.html", page_context(request, "automations", flows=flows, notice=labels[automation]))


@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    return templates.TemplateResponse("settings.html", page_context(request, "settings"))


@app.post("/settings", response_class=HTMLResponse)
def save_settings(request: Request, workspace: str = Form(...), service: str = Form(...)):
    settings_state["workspace"] = workspace.strip() or settings_state["workspace"]
    settings_state["service"] = service.strip() or settings_state["service"]
    activities.insert(0, ("Settings", "Workspace configuration updated", "just now"))
    return templates.TemplateResponse("settings.html", page_context(request, "settings", notice="Workspace settings saved."))


@app.get("/health")
def health():
    return {"status":"ok", "service":"clientgrowth-ai-hub", "version":"1.2.0", "time":datetime.now(timezone.utc).isoformat()}


@app.get("/api")
def api_root():
    return {"status":"ok", "service":"clientgrowth-ai-hub", "version":"1.2.0", "endpoints":["/api/health","/api/leads","/api/leads/{id}/stage","/api/audit","/api/outreach","/api/automations/{automation}","/health"]}


@app.get("/api/health")
def api_health():
    return {"status":"ok", "service":"clientgrowth-ai-hub", "version":"1.2.0", "time":datetime.now(timezone.utc).isoformat()}


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
    message = make_outreach(company, signal, service)
    activities.insert(0, ("Outreach Studio", f"API draft prepared for {company}", "just now"))
    return {"status":"ok", "data":{"company":company,"message":message}}


@app.post("/api/automations/{automation}")
def api_automation(automation: str):
    allowed = {"lead-discovery":"Lead discovery queued","website-audit":"Website audit queued","outreach":"Outreach preparation queued","follow-up":"Follow-up check queued"}
    if automation not in allowed:
        raise HTTPException(404, "Automation not found")
    activities.insert(0, ("Automation Center", allowed[automation], "just now"))
    return {"status":"queued", "automation":automation, "message":allowed[automation]}
