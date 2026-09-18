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
app = FastAPI(title="ClientGrowth AI Command Center", version="2.2.0")
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
        "ai": bool(os.getenv("OPENROUTER_API_KEY") or (os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL"))),
        "openrouter_free": bool(os.getenv("OPENROUTER_API_KEY")),
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

@app.get("/pipeline", response_class=HTMLResponse)
def pipeline(request: Request): return templates.TemplateResponse("pipeline.html", context(request,"pipeline",stages=stages))

@app.post("/pipeline/{lead_id}/stage", response_class=HTMLResponse)
def move_lead(request: Request, lead_id: int, stage: str=Form(...)):
    require_db()
    if stage not in stages: raise HTTPException(400,"Invalid stage")
    lead=update_stage(lead_id,stage)
    if not lead: raise HTTPException(404,"Lead not found")
    add_activity("Opportunity Board",f"Moved {lead['name']} to {stage}"); return templates.TemplateResponse("pipeline.html", context(request,"pipeline",stages=stages,notice=f"{lead['name']} moved to {stage}."))

@app.get("/audit", response_class=HTMLResponse)
def audit(request: Request): return templates.TemplateResponse("audit.html", context(request,"audit"))

@app.post("/audit", response_class=HTMLResponse)
def run_audit(request: Request, url: str=Form(...)):
    try: report=website_audit(url); error=None
    except Exception as exc: report=None; error=str(exc)
    if report and configured(): add_activity("Website X-Ray",f"Audited {report['url']}")
    return templates.TemplateResponse("audit.html", context(request,"audit",report=report,error=error))

@app.get("/intelligence", response_class=HTMLResponse)
def intelligence_page(request: Request):
    return templates.TemplateResponse("intelligence.html", context(request,"intelligence",ready=integration_state()))

@app.post("/intelligence", response_class=HTMLResponse)
def intelligence_run(request: Request, query: str=Form(...), location: str=Form(""), limit: int=Form(10)):
    try:
        results=google_places_search(query,location,min(max(limit,1),20))
        rows=[{**r,"qualification":classify_prospect(r),"whatsapp_link":whatsapp_link(r.get("phone"))} for r in results]
        error=None
    except Exception as exc: rows=[]; error=str(exc)
    return templates.TemplateResponse("intelligence.html", context(request,"intelligence",ready=integration_state(),rows=rows,query=query,location=location,error=error))

@app.get("/outreach", response_class=HTMLResponse)
def outreach(request: Request, company: str="", signal: str="", service: str=""): return templates.TemplateResponse("outreach.html", context(request,"outreach",prefill={"company":company,"signal":signal,"service":service}))

@app.post("/outreach", response_class=HTMLResponse)
def generate_outreach(request: Request, company: str=Form(...), signal: str=Form(...), service: str=Form(...)):
    try: message=openai_generate("You are a professional B2B outreach writer. Write one concise, specific, non-hype first-contact message. Do not invent facts about the prospect. Return only the message.",f"Company: {company}\nObserved signal: {signal}\nService offered: {service}"); error=None
    except Exception as exc: message=None; error=str(exc)
    if message and configured(): add_activity("Outreach Studio",f"Generated AI outreach for {company}")
    return templates.TemplateResponse("outreach.html", context(request,"outreach",message=message,error=error,prefill={"company":company,"signal":signal,"service":service}))

@app.get("/resume", response_class=HTMLResponse)
def resume(request: Request): return templates.TemplateResponse("resume.html", context(request,"resume"))

@app.post("/resume", response_class=HTMLResponse)
def resume_action(request: Request, mode: str=Form(...), target: str=Form("Web Developer"), job: str=Form("")):
    try:
        prompt={"resume":"Create a concise professional resume profile for a web developer and digital systems builder. Use only the supplied facts.","match":"Analyze the job description against the candidate profile. Identify exact matches, missing evidence and suggested wording.","profile":"Create a professional LinkedIn-style headline and about section for a web developer and digital systems builder."}[mode]
        source=f"Candidate: Emmanuel, web development, WordPress, WooCommerce, Python, FastAPI, responsive websites, automation and AI-powered digital systems.\nTarget: {target}\nJob description: {job}"
        result=openai_generate(prompt,source); error=None
    except Exception as exc: result=None; error=str(exc)
    return templates.TemplateResponse("resume.html", context(request,"resume",result=result,error=error))

@app.get("/automations", response_class=HTMLResponse)
def automations(request: Request):
    flows=[("Lead discovery","Google Places → qualify → save","Live","lead-discovery"),("Website intelligence","URL → live HTTP audit → opportunity classification","Live","website-audit"),("AI outreach","Prospect signal → OpenAI → review","Live","outreach"),("Email/WhatsApp","Opt-in recipients → provider → delivery","Provider required","messaging"),("Follow-up","Persistent opportunity → scheduled follow-up","Scheduler required","follow-up")]
    return templates.TemplateResponse("automations.html", context(request,"automations",flows=flows))

@app.post("/automations/run", response_class=HTMLResponse)
def run_automation(request: Request, automation: str=Form(...)):
    target={"lead-discovery":"/intelligence","website-audit":"/audit","outreach":"/outreach","messaging":"/settings","follow-up":"/settings"}.get(automation,"/settings")
    return templates.TemplateResponse("automations.html", context(request,"automations",flows=[("Lead discovery","Google Places → qualify → save","Live","lead-discovery"),("Website intelligence","URL → live HTTP audit → opportunity classification","Live","website-audit"),("AI outreach","Prospect signal → OpenAI → review","Live","outreach"),("Email/WhatsApp","Opt-in recipients → provider → delivery","Provider required","messaging"),("Follow-up","Persistent opportunity → scheduled follow-up","Scheduler required","follow-up")],notice=f"Open {target} to run this workflow with real inputs."))

@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request): return templates.TemplateResponse("settings.html", context(request,"settings"))

@app.post("/settings", response_class=HTMLResponse)
def save_settings_route(request: Request, workspace: str=Form(...), service: str=Form(...)):
    require_db(); save_settings(workspace.strip(),service.strip()); add_activity("Settings","Workspace configuration updated"); return templates.TemplateResponse("settings.html", context(request,"settings",notice="Workspace settings saved."))

@app.get("/health")
def health():
    db=db_status(); return {"status":"ok" if db["connected"] else "degraded","service":"clientgrowth-ai-hub","version":"2.2.0","database":db,"integrations":integration_state(),"time":datetime.now(timezone.utc).isoformat()}

@app.get("/api")
def api_root(): return {"status":"ok","service":"clientgrowth-ai-hub","version":"2.1.1","engines":{"database":"PostgreSQL","website_audit":"live_http","maps":"Google Places API","ai":"OpenRouter free-model router (OpenAI-compatible) with OpenAI fallback","qualification":"rules+live provider data"},"endpoints":["/api/health","/api/leads","/api/maps/search","/api/prospect/qualify","/api/whatsapp/check","/api/outreach","/api/campaign/guard"]}

@app.get("/api/health")
def api_health(): return health()

@app.get("/api/leads")
def api_leads(): require_db(); data=list_leads(); return {"status":"ok","count":len(data),"data":data}

@app.post("/api/leads")
def api_create_lead(payload: dict):
    require_db(); required=["name","type","location","signal"]
    if any(not str(payload.get(k,"")).strip() for k in required): raise HTTPException(400,"name, type, location and signal are required")
    lead=create_lead({**payload,"score":int(payload.get("score",0))}); add_activity("Lead Radar",f"Added {lead['name']} through API"); return {"status":"created","data":lead}

@app.patch("/api/leads/{lead_id}/stage")
def api_move_lead(lead_id:int,payload:dict):
    require_db(); stage=payload.get("stage")
    if stage not in stages: raise HTTPException(400,"Invalid stage")
    lead=update_stage(lead_id,stage)
    if not lead: raise HTTPException(404,"Lead not found")
    add_activity("Opportunity Board",f"Moved {lead['name']} to {stage}"); return {"status":"updated","data":lead}

@app.post("/api/maps/search")
def api_maps(payload:dict):
    query=str(payload.get("query","")).strip(); location=str(payload.get("location","")).strip()
    if not query: raise HTTPException(400,"query is required")
    results=google_places_search(query,location,int(payload.get("max_results",10)))
    return {"status":"ok","data":[{**r,"qualification":classify_prospect(r),"whatsapp_link":whatsapp_link(r.get("phone"))} for r in results]}

@app.post("/api/prospect/qualify")
def api_qualify(payload:dict): return {"status":"ok","data":classify_prospect(payload)}

@app.post("/api/whatsapp/check")
def api_whatsapp_check(payload:dict):
    phone=str(payload.get("phone","")).strip()
    return {"status":"ok","phone":phone,"whatsapp_status":"UNKNOWN — public data cannot reliably prove WhatsApp registration","chat_link":whatsapp_link(phone)}

@app.post("/api/audit")
def api_audit(payload:dict):
    url=str(payload.get("url","")).strip()
    if not url: raise HTTPException(400,"url is required")
    report=website_audit(url)
    if configured(): add_activity("Website X-Ray",f"API audit completed for {report['url']}")
    return {"status":"ok","data":report}

@app.post("/api/outreach")
def api_outreach(payload:dict):
    company=str(payload.get("company","")).strip(); signal=str(payload.get("signal","")).strip(); service=str(payload.get("service","")).strip()
    if not company or not signal or not service: raise HTTPException(400,"company, signal and service are required")
    message=openai_generate("You are a professional B2B outreach writer. Write one concise, specific, non-hype first-contact message. Do not invent facts about the prospect. Return only the message.",f"Company: {company}\nObserved signal: {signal}\nService offered: {service}")
    if configured(): add_activity("Outreach Studio",f"API AI draft prepared for {company}")
    return {"status":"ok","data":{"company":company,"message":message}}

@app.post("/api/campaign/guard")
def api_campaign_guard(payload:dict):
    recipients=payload.get("recipients",[])
    return {"status":"ok","data":campaign_guard(recipients)}

@app.post("/api/automations/{automation}")
def api_automation(automation:str):
    if automation not in {"lead-discovery","website-audit","outreach","follow-up","messaging"}: raise HTTPException(404,"Automation not found")
    return {"status":"ready","automation":automation,"message":"Workflow is available when its live input/provider is configured. No simulated job was created."}
