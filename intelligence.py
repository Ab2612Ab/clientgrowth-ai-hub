from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import re


def _probe_website(url, timeout=6):
    """Perform a lightweight live public HTTP check; never invent a result."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    request = Request(url, headers={"User-Agent": "ClientGrowthAI/2.2 WebsiteAudit"})
    try:
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            status = getattr(response, "status", 200)
            content_type = response.headers.get("content-type", "")
            raw = response.read(250_000)
            text = raw.decode("utf-8", errors="ignore") if "text" in content_type or not content_type else ""
            lower = text.lower()
            title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.I | re.S)
            viewport = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', text, re.I))
            forms = len(re.findall(r"<form\b", text, re.I))
            cta_terms = len(re.findall(r"\b(contact|book|quote|call|whatsapp|enquire|schedule|get started)\b", lower))
            return {
                "reachable": True,
                "status_code": status,
                "final_url": final_url,
                "https": final_url.lower().startswith("https://"),
                "title_present": bool(title and title.group(1).strip()),
                "h1_present": bool(h1 and re.sub(r"<[^>]+>", " ", h1.group(1)).strip()),
                "mobile_viewport": viewport,
                "forms": forms,
                "cta_signals": cta_terms,
            }
    except Exception as exc:
        return {"reachable": False, "status_code": None, "final_url": url, "error": str(exc)[:180]}


def classify_prospect(place):
    """Classify a real Google Places result plus a live public website probe."""
    website = (place.get("website") or "").strip()
    phone = (place.get("phone") or "").strip()
    rating = place.get("rating") or 0
    reviews = place.get("reviews") or 0
    signals = []
    score = 0
    probe = None

    if not website:
        website_status = "NO WEBSITE"
        signals.append("No website URL returned by Google Places")
        score += 45
    else:
        probe = _probe_website(website)
        if not probe.get("reachable"):
            website_status = "WEBSITE UNREACHABLE"
            signals.append("Website URL exists but the live site could not be reached")
            score += 35
        elif not probe.get("https"):
            website_status = "OUTDATED / HTTP"
            signals.append("Live website uses HTTP instead of HTTPS")
            score += 30
        elif not probe.get("mobile_viewport"):
            website_status = "OUTDATED / MOBILE SIGNAL"
            signals.append("Live page is missing a mobile viewport declaration")
            score += 25
        elif not probe.get("title_present") or not probe.get("h1_present"):
            website_status = "WEAK / INCOMPLETE"
            signals.append("Live page is missing a title or H1 signal")
            score += 20
        else:
            website_status = "WEBSITE ACTIVE"
            score += 5
        if probe.get("forms", 0) == 0:
            signals.append("No HTML form detected on the checked page")
            score += 5
        if probe.get("cta_signals", 0) == 0:
            signals.append("No obvious contact/booking/quote CTA detected")
            score += 10

    if rating and rating >= 4.0 and reviews >= 20:
        signals.append("Established Google presence")
        score += 10
    if reviews >= 100:
        signals.append("High review volume")
        score += 10
    if phone:
        signals.append("Public phone number available")
        score += 5
    if website and phone:
        signals.append("Has both website and phone contact")

    priority = "HIGH" if score >= 55 else "MEDIUM" if score >= 30 else "LOW"
    return {
        "priority": priority,
        "score": min(score, 100),
        "website_status": website_status,
        "signals": signals,
        "website_probe": probe,
        "whatsapp_status": "UNKNOWN — requires authorized WhatsApp provider verification",
    }


def whatsapp_link(phone):
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if not digits:
        return None
    return f"https://wa.me/{digits}"


def campaign_guard(recipients):
    """Require explicit consent before automated bulk messaging."""
    blocked = [r for r in recipients if not r.get("opted_in")]
    return {
        "allowed": not blocked,
        "blocked_count": len(blocked),
        "reason": None if not blocked else "Recipients without recorded opt-in cannot be sent automated bulk messages.",
    }
