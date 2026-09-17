import json
import os
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser
from urllib.parse import urlparse, quote


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.h1 = []
        self.links = []
        self.forms = 0
        self.inputs = 0
        self.viewport = False
        self.text = []
        self._title = False
        self._h1 = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title": self._title = True
        if tag == "h1": self._h1 = True
        if tag == "a" and attrs.get("href"): self.links.append(attrs["href"])
        if tag == "form": self.forms += 1
        if tag in {"input", "textarea", "select"}: self.inputs += 1
        if tag == "meta" and attrs.get("name", "").lower() == "viewport": self.viewport = True

    def handle_endtag(self, tag):
        if tag == "title": self._title = False
        if tag == "h1": self._h1 = False

    def handle_data(self, data):
        value = " ".join(data.split())
        if not value: return
        self.text.append(value)
        if self._title: self.title += value
        if self._h1: self.h1.append(value)


def http_get(url, timeout=12):
    request = urllib.request.Request(url, headers={"User-Agent": "ClientGrowthAI/2.2 (+website-audit)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(1_500_000)
        return response.geturl(), response.status, response.headers.get_content_type(), body


def normalize_url(value):
    target = value.strip()
    if "://" not in target: target = "https://" + target
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Enter a valid HTTP or HTTPS website URL.")
    return target


def website_audit(value):
    target = normalize_url(value)
    final_url, status, content_type, body = http_get(target)
    html = body.decode("utf-8", errors="ignore") if "html" in content_type else ""
    parser = PageParser(); parser.feed(html)
    checks = []
    score = 100
    if status >= 400:
        score -= 35; checks.append(("Availability", "Critical", f"The page returned HTTP {status}."))
    else:
        checks.append(("Availability", "Pass", f"The page returned HTTP {status}."))
    if final_url.startswith("https://"):
        checks.append(("HTTPS", "Pass", "The audited page is served over HTTPS."))
    else:
        score -= 15; checks.append(("HTTPS", "Needs attention", "The audited page is not using HTTPS."))
    if parser.viewport:
        checks.append(("Mobile viewport", "Pass", "A responsive viewport declaration was found."))
    else:
        score -= 15; checks.append(("Mobile viewport", "Needs attention", "No responsive viewport declaration was found."))
    if parser.title.strip():
        checks.append(("Page title", "Pass", f"Detected title: {parser.title[:120]}"))
    else:
        score -= 8; checks.append(("Page title", "Needs attention", "No HTML title was detected."))
    if parser.h1:
        checks.append(("Primary heading", "Pass", f"Detected H1: {parser.h1[0][:120]}"))
    else:
        score -= 8; checks.append(("Primary heading", "Opportunity", "No H1 was detected in the fetched HTML."))
    if parser.forms:
        checks.append(("Lead capture", "Pass", f"Detected {parser.forms} form(s) and {parser.inputs} form control(s)."))
    else:
        score -= 12; checks.append(("Lead capture", "Opportunity", "No HTML form was detected; conversion may rely on another mechanism."))
    ctas = [x for x in parser.links if any(k in x.lower() for k in ("contact", "book", "quote", "demo", "signup", "start"))]
    if ctas:
        checks.append(("Conversion paths", "Pass", f"Detected {len(ctas)} likely conversion link(s)."))
    else:
        score -= 10; checks.append(("Conversion paths", "Opportunity", "No obvious contact, booking, quote, demo or signup link was detected."))
    return {"url": final_url, "status": status, "score": max(0, min(100, score)), "title": parser.title.strip(), "h1": parser.h1[:5], "links": len(parser.links), "forms": parser.forms, "findings": checks}


def _place_row(p, source):
    return {
        "provider_id": p.get("id") or p.get("place_id"),
        "name": p.get("displayName", {}).get("text", "") if isinstance(p.get("displayName"), dict) else p.get("name", ""),
        "address": p.get("formattedAddress") or p.get("display_name", ""),
        "website": p.get("websiteUri") or p.get("website"),
        "phone": p.get("nationalPhoneNumber") or p.get("phone"),
        "maps_url": p.get("googleMapsUri") or p.get("maps_url"),
        "rating": p.get("rating"),
        "reviews": p.get("userRatingCount") or p.get("reviews"),
        "source": source,
    }


def google_places_search(query, location=None, max_results=10):
    key = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_PLACES_API_KEY")
    if not key:
        return free_business_search(query, location, max_results)
    url = "https://places.googleapis.com/v1/places:searchText"
    payload = {"textQuery": query, "pageSize": min(max_results, 20)}
    if location: payload["textQuery"] = f"{query} in {location}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type":"application/json", "X-Goog-Api-Key":key, "X-Goog-FieldMask":"places.id,places.displayName,places.formattedAddress,places.websiteUri,places.nationalPhoneNumber,places.googleMapsUri,places.rating,places.userRatingCount"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="ignore")[:600]
        raise RuntimeError(f"Google Places request failed ({exc.code}): {detail}")
    return [_place_row(p, "google-places") for p in raw.get("places", [])]


def free_business_search(query, location=None, max_results=10):
    """Keyless public business discovery using OpenStreetMap Nominatim.
    This is a fallback, not a Google Maps replacement. It uses public place data
    and identifies the source so users can distinguish providers."""
    search = f"{query} {location}".strip() if location else query.strip()
    if not search:
        raise ValueError("A business query is required.")
    url = "https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&limit=" + str(min(max_results, 10)) + "&q=" + quote(search)
    req = urllib.request.Request(url, headers={"User-Agent": "ClientGrowthAI/2.2 (business-discovery)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="ignore")[:500]
        raise RuntimeError(f"OpenStreetMap discovery failed ({exc.code}): {detail}")
    results = []
    for p in raw:
        address = p.get("display_name", "")
        maps_url = f"https://www.openstreetmap.org/{p.get('osm_type','node')}/{p.get('osm_id')}" if p.get("osm_id") else None
        results.append(_place_row({
            "place_id": p.get("place_id"),
            "name": p.get("name") or address.split(",")[0],
            "display_name": address,
            "maps_url": maps_url,
        }, "openstreetmap"))
    return results


def openai_generate(instruction, input_text):
    key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    if not key or not model:
        raise RuntimeError("OpenAI is optional but not connected. Add OPENAI_API_KEY and OPENAI_MODEL to enable AI generation.")
    payload = {"model": model, "instructions": instruction, "input": input_text}
    data = json.dumps(payload).encode()
    req = urllib.request.Request("https://api.openai.com/v1/responses", data=data, method="POST", headers={"Content-Type":"application/json", "Authorization":f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="ignore")[:800]
        raise RuntimeError(f"OpenAI request failed ({exc.code}): {detail}")
    output = raw.get("output", [])
    texts = []
    for item in output:
        for part in item.get("content", []):
            if part.get("type") == "output_text" and part.get("text"):
                texts.append(part["text"])
    return "\n".join(texts).strip()
