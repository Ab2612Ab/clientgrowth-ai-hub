from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).parent
app = FastAPI(title="ClientGrowth AI Command Center")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

leads = [
    {"name":"Northstar Property Group","type":"Property Management","location":"Atlanta, GA","signal":"Outdated website","score":94,"stage":"New","website":"northstar.example"},
    {"name":"Apex Auto Collective","type":"Automotive","location":"Charlotte, NC","signal":"No mobile CTA","score":88,"stage":"Qualified","website":"apexauto.example"},
    {"name":"Lumen Dental Studio","type":"Healthcare","location":"Austin, TX","signal":"Slow booking flow","score":81,"stage":"Contacted","website":"lumendental.example"},
    {"name":"Harborline Creative","type":"Creative Agency","location":"Miami, FL","signal":"Growth hiring","score":76,"stage":"New","website":"harborline.example"},
]

activities = [
    ("Website X-Ray", "4 prospects analyzed", "2 min ago"),
    ("Lead Radar", "12 new opportunities surfaced", "18 min ago"),
    ("Outreach Studio", "3 personalized drafts prepared", "41 min ago"),
]

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    stats = {"leads": len(leads)+128, "qualified": 47, "opportunities": 19, "reply_rate": "18.4%"}
    return templates.TemplateResponse("dashboard.html", {"request":request, "stats":stats, "leads":leads, "activities":activities, "active":"dashboard"})

@app.get("/radar", response_class=HTMLResponse)
def radar(request: Request):
    return templates.TemplateResponse("radar.html", {"request":request, "leads":leads, "active":"radar"})

@app.get("/pipeline", response_class=HTMLResponse)
def pipeline(request: Request):
    stages = ["New","Qualified","Contacted","Replied"]
    return templates.TemplateResponse("pipeline.html", {"request":request, "leads":leads, "stages":stages, "active":"pipeline"})

@app.get("/audit", response_class=HTMLResponse)
def audit(request: Request):
    return templates.TemplateResponse("audit.html", {"request":request, "active":"audit"})

@app.post("/audit", response_class=HTMLResponse)
def run_audit(request: Request, url: str = Form(...)):
    clean = url.replace("https://","").replace("http://","").strip("/")
    report = {
        "url": clean,
        "score": 63,
        "findings":[
            ("Mobile conversion", "Needs attention", "Primary actions should be easier to reach on small screens."),
            ("Trust signals", "Opportunity", "Add reviews, case studies and recognizable proof near key CTAs."),
            ("Performance", "Opportunity", "Compress hero media and defer non-critical assets."),
            ("Lead capture", "Needs attention", "Use a shorter contact path with one clear conversion goal."),
        ]
    }
    return templates.TemplateResponse("audit.html", {"request":request, "active":"audit", "report":report})

@app.get("/outreach", response_class=HTMLResponse)
def outreach(request: Request):
    return templates.TemplateResponse("outreach.html", {"request":request, "active":"outreach", "leads":leads})

@app.post("/outreach", response_class=HTMLResponse)
def generate_outreach(request: Request, company: str = Form(...), signal: str = Form(...), service: str = Form(...)):
    message = f"Hi {company} team,\n\nI came across your business and noticed {signal.lower()}. I build focused websites and digital systems that make it easier for the right prospects to understand the offer and take action.\n\nI can put together a short visual concept around {service.lower()} so you can see the direction before deciding on anything.\n\nBest,\nEmmanuel"
    return templates.TemplateResponse("outreach.html", {"request":request, "active":"outreach", "leads":leads, "message":message})

@app.get("/resume", response_class=HTMLResponse)
def resume(request: Request):
    return templates.TemplateResponse("resume.html", {"request":request, "active":"resume"})

@app.get("/automations", response_class=HTMLResponse)
def automations(request: Request):
    flows = [
        ("Lead discovery", "Search → qualify → enrich → pipeline", "Ready"),
        ("Website audit", "URL → checks → opportunity report", "Ready"),
        ("Outreach", "Signal → personalization → review queue", "Ready"),
        ("Follow-up", "No reply → timed reminder → task", "Planned"),
    ]
    return templates.TemplateResponse("automations.html", {"request":request, "active":"automations", "flows":flows})

@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request":request, "active":"settings"})

@app.get("/health")
def health():
    return {"status":"ok", "service":"clientgrowth-ai-hub", "time":datetime.utcnow().isoformat()}
