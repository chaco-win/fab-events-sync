import os, re, time, hashlib, logging
from datetime import timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser, tz
import tomli

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def cfg_load():
    cfg = {}
    if os.path.exists("config.toml"):
        with open("config.toml", "rb") as f:
            cfg = tomli.load(f)

    return {
        "CAL_ID": os.environ.get("CALENDAR_ID", "").strip(),
        "TZ": os.environ.get("TIMEZONE", cfg.get("TIMEZONE", "America/Chicago")),
        "MAJOR_TYPES": set(cfg.get("MAJOR_TYPES", [])),
        "TYPE_RADIUS": {k: float(v) for k, v in cfg.get("TYPE_RADIUS_MILES", {}).items()},
        "TYPE_COUNTRY_WL": {k: [s.lower() for s in v] for k, v in cfg.get("TYPE_COUNTRY_WHITELIST", {}).items()},
        "DEFAULT_H": int(cfg.get("DEFAULT_EVENT_HOURS", 6)),
        "LOCAL_URL": os.environ.get("FAB_LOCAL_URL") or os.environ.get("FAB_BASE_URL", ""),
        "GLOBAL_URL": os.environ.get("FAB_GLOBAL_URL", ""),
        "SA_PATH": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
    }

def http_pages(start_url):
    """Yield (soup, url) across pagination."""
    if not start_url:
        return
    url = start_url
    session = requests.Session()
    headers = {"User-Agent": "fab-sync/1.0 (+weekly, noncommercial)"}
    while url:
        logging.info(f"GET {url}")
        r = session.get(url, timeout=30, headers=headers)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        yield soup, url
        nxt = soup.find("a", attrs={"rel": "next"}) or soup.find("a", string=re.compile(r"^\s*(Next|>>)\s*$", re.I))
        url = urljoin(url, nxt["href"]) if nxt and nxt.get("href") else None
        if url:
            time.sleep(0.5)

def _text(el):
    return el.get_text(" ", strip=True) if el else ""

def parse_events(soup):
    """
    Heuristic scraper: find 'Details' links; walk up to the card; pull title/type/datetime/address/distance.
    """
    out = []
    for a in soup.find_all("a", string=re.compile(r"Details", re.I)):
        # card block
        card = a
        for _ in range(3):
            card = card.parent if card and card.parent else card

        # title/type
        title_el = None
        for tag in ("h1","h2","h3","h4"):
            title_el = card.find(tag)
            if title_el: break
        title_text = _text(title_el)
        ev_type, ev_title = None, title_text
        # Common patterns: "Calling: City", "Pro Quest+ Store", etc.
        m = re.match(r"^\s*([A-Za-z +'\-]+):?\s+(.*)$", title_text)
        if m:
            ev_type, ev_title = m.group(1).strip(), m.group(2).strip()
        else:
            # Sometimes type is a badge near title
            badge = card.find(class_=re.compile(r"(badge|label|type)", re.I))
            if badge:
                ev_type = _text(badge)

        # meta text to search lines
        meta = _text(card)

        # datetime
        dt_line = None
        for line in meta.splitlines():
            line_s = line.strip()
            if re.search(r"\b(AM|PM)\b|\d{1,2}:\d{2}", line_s) or re.search(r"\bMon|Tue|Wed|Thu|Fri|Sat|Sun\b", line_s, re.I):
                dt_line = line_s; break
        start = None
        if dt_line:
            try:
                start = dateparser.parse(dt_line, fuzzy=True)
            except Exception:
                start = None

        # distance "(123 mi)"
        dist = None
        dm = re.search(r"\(([\d.]+)\s*mi\)", meta)
        if dm:
            try:
                dist = float(dm.group(1))
            except ValueError:
                dist = None

        # address guess: first line with street/city/state/country patterns
        address = None
        for l in [l.strip() for l in meta.splitlines() if l.strip()]:
            if re.search(r"\d{2,}", l) or re.search(r"\b(Street|St\.|Road|Rd\.|Ave|Avenue|Blvd|Texas|TX|USA|United States|US|Canada|United Kingdom|UK|Australia|NZ)\b", l, re.I):
                address = l; break

        details_url = urljoin("https://fabtcg.com", a.get("href"))

        if ev_title:
            out.append({
                "type": (ev_type or "").strip(),
                "title": ev_title.strip(),
                "start": start,
                "address": address or "",
                "distance_mi": dist,
                "details": details_url,
            })
    return out

def pass_country_whitelist(ev, wl_map):
    if not wl_map:
        return True
    t = ev["type"]
    if t not in wl_map:
        return True
    addr = (ev.get("address") or "").lower()
    for token in wl_map[t]:
        if token in addr:
            return True
    # Also treat US state abbreviations as USA
    if t in wl_map and any(tok in wl_map[t] for tok in ("usa","united states","us")):
        if re.search(r",\s*[A-Z]{2}\s*(?:,|$)", ev.get("address","")):
            return True
    return False

def include_global(ev, majors, wl_map):
    return (ev["type"] in majors) and pass_country_whitelist(ev, wl_map)

def include_local(ev, type_radius):
    if ev["type"] not in type_radius:
        return False
    if ev["distance_mi"] is None:
        return False
    return ev["distance_mi"] <= float(type_radius[ev["type"]])

def make_uid(ev):
    base = f"{ev.get('details','')}|{ev.get('start').isoformat() if ev.get('start') else 'na'}"
    return hashlib.sha1(base.encode()).hexdigest() + "@fabtcg"

def gcal_service(sa_path):
    scopes = ["https://www.googleapis.com/auth/calendar"]
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=scopes)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def upsert_event(svc, cal_id, ev, tzname, default_hours):
    if not ev["start"]:
        logging.warning(f"Skip (no start): {ev['type']} — {ev['title']}")
        return
    uid = make_uid(ev)
    start_local = ev["start"].astimezone(tz.gettz(tzname))
    end_local = start_local + timedelta(hours=default_hours)
    body = {
        "summary": f"{ev['type']}: {ev['title']}".strip(": "),
        "location": ev.get("address",""),
        "description": (f"Official listing: {ev['details']}" if ev.get("details") else ""),
        "start": {"dateTime": start_local.isoformat(), "timeZone": tzname},
        "end": {"dateTime": end_local.isoformat(), "timeZone": tzname},
        "iCalUID": uid,
        "source": {"title": "FaB Events", "url": ev.get("details") or "https://fabtcg.com/en/events/"},
    }
    try:
        existing = svc.events().list(calendarId=cal_id, iCalUID=uid, maxResults=1).execute().get("items", [])
        if existing:
            svc.events().update(calendarId=cal_id, eventId=existing[0]["id"], body=body).execute()
            logging.info(f"Updated: {body['summary']}")
        else:
            svc.events().insert(calendarId=cal_id, body=body).execute()
            logging.info(f"Inserted: {body['summary']}")
    except HttpError as e:
        logging.error(f"Google API error: {e}")
        raise

def main():
    cfg = cfg_load()
    if not cfg["CAL_ID"]:
        raise SystemExit("Missing CALENDAR_ID env.")
    if not cfg["SA_PATH"] or not os.path.exists(cfg["SA_PATH"]):
        raise SystemExit("GOOGLE_APPLICATION_CREDENTIALS not set or file missing.")
    svc = gcal_service(cfg["SA_PATH"])

    seen = set()

    # GLOBAL: majors (optionally country-filtered)
    if cfg["GLOBAL_URL"]:
        for soup, _ in http_pages(cfg["GLOBAL_URL"]):
            for ev in parse_events(soup):
                if not include_global(ev, cfg["MAJOR_TYPES"], cfg["TYPE_COUNTRY_WL"]):
                    continue
                uid = make_uid(ev)
                if uid in seen:
                    continue
                seen.add(uid)
                upsert_event(svc, cfg["CAL_ID"], ev, cfg["TZ"], cfg["DEFAULT_H"])

    # LOCAL: per-type distance caps
    if cfg["LOCAL_URL"]:
        for soup, _ in http_pages(cfg["LOCAL_URL"]):
            for ev in parse_events(soup):
                if not include_local(ev, cfg["TYPE_RADIUS"]):
                    continue
                uid = make_uid(ev)
                if uid in seen:
                    continue
                seen.add(uid)
                upsert_event(svc, cfg["CAL_ID"], ev, cfg["TZ"], cfg["DEFAULT_H"])

    logging.info(f"Done. Upserts: {len(seen)}")

if __name__ == "__main__":
    main()
