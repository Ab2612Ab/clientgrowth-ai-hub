from urllib.parse import quote


def classify_prospect(place):
    """Classify a real Google Places result using only returned public fields.
    Does not claim WhatsApp registration; that requires an authorized WhatsApp API.
    """
    website = (place.get("website") or "").strip()
    phone = (place.get("phone") or "").strip()
    rating = place.get("rating") or 0
    reviews = place.get("reviews") or 0
    signals = []
    score = 0
    if not website:
        website_status = "NO WEBSITE"
        signals.append("No website URL returned by Google Places")
        score += 35
    else:
        website_status = "WEBSITE PRESENT"
        score += 5
    if website and website.startswith("http://"):
        website_status = "OUTDATED / HTTP"
        signals.append("Website uses HTTP instead of HTTPS")
        score += 25
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
    return {"priority": priority, "score": min(score, 100), "website_status": website_status, "signals": signals,
            "whatsapp_status": "UNKNOWN — requires authorized WhatsApp provider verification"}


def whatsapp_link(phone):
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if not digits:
        return None
    return f"https://wa.me/{digits}"


def campaign_guard(recipients):
    """Require explicit consent before automated bulk messaging."""
    blocked = [r for r in recipients if not r.get("opted_in")]
    return {"allowed": not blocked, "blocked_count": len(blocked),
            "reason": None if not blocked else "Recipients without recorded opt-in cannot be sent automated bulk messages."}
