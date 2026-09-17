# ClientGrowth AI Command Center

A visual, Python-powered workspace for prospect discovery, opportunity intelligence, website X-Ray audits, outreach preparation, resume positioning, and workflow planning.

## Stack

- Python 3.11+
- FastAPI
- Jinja2 server-rendered UI
- HTML/CSS
- Vercel-compatible API entrypoint

## Run locally

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.

## Routes

`/` overview · `/radar` lead radar · `/pipeline` opportunity board · `/audit` website X-Ray · `/outreach` outreach studio · `/resume` resume lab · `/automations` automation center · `/settings` settings · `/health` health check.

## Production integrations

The current experience uses safe local sample data and server-side demo workflows. API keys and external providers should be connected through environment variables before enabling live prospect discovery, enrichment, messaging, or AI generation.
