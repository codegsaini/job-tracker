import re
import time
from datetime import datetime, timedelta, timezone

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept": "application/json, text/html;q=0.9"})


def _request(method, url, retries=3, **kw):
    """HTTP request that backs off and retries on rate limits / server errors."""
    kw.setdefault("timeout", 30)
    for attempt in range(retries + 1):
        r = session.request(method, url, **kw)
        if r.status_code not in (429, 500, 502, 503, 504) or attempt == retries:
            break
        retry_after = r.headers.get("Retry-After", "")
        time.sleep(int(retry_after) if retry_after.isdigit() else 5 * 3 ** attempt)
    r.raise_for_status()
    return r


def get(url, **kw):
    return _request("GET", url, **kw)


def post(url, **kw):
    return _request("POST", url, **kw)


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    """Normalise a datetime / epoch / ISO string to an ISO-8601 UTC string (or None)."""
    if dt is None or dt == "":
        return None
    if isinstance(dt, (int, float)):
        if dt > 1e11:  # milliseconds
            dt /= 1000
        dt = datetime.fromtimestamp(dt, timezone.utc)
    elif isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def days_ago(n):
    return iso(now_utc() - timedelta(days=n))


def make_job(source, native_id, title, company, location, url, posted=None, remote=None, **extra):
    title = " ".join((title or "").split())
    location = " ".join((location or "").split())
    if remote is None:
        remote = "remote" in location.lower()
    return {
        "id": f"{source}:{native_id}",
        "title": title,
        "company": " ".join((company or "").split()),
        "location": location,
        "url": url,
        "source": source,
        "posted": iso(posted),
        "remote": bool(remote),
        **extra,
    }


def _word_pattern(text):
    return re.compile(r"(?<![a-z0-9])" + re.escape(text.lower()) + r"(?![a-z0-9])")


class Matcher:
    def __init__(self, cfg):
        self.keywords = [_word_pattern(k) for k in cfg.get("keywords") or []]
        self.exclude = [_word_pattern(k) for k in cfg.get("exclude") or []]
        self.locations = []
        for loc in cfg.get("locations") or []:
            if loc.startswith("re:"):
                self.locations.append(re.compile(loc[3:], re.I))
            else:
                self.locations.append(re.compile(re.escape(loc), re.I))

    def title_ok(self, title):
        t = title.lower()
        if any(p.search(t) for p in self.exclude):
            return False
        return not self.keywords or any(p.search(t) for p in self.keywords)

    def location_ok(self, job):
        if not self.locations:
            return True
        if job.get("remote") and any(p.pattern.lower() == "remote" for p in self.locations):
            return True
        return any(p.search(job["location"]) for p in self.locations)

    def ok(self, job):
        return self.title_ok(job["title"]) and self.location_ok(job)


def fingerprint(job):
    """Cross-source duplicate key: same title at the same company."""
    return re.sub(r"[^a-z0-9]", "", (job["title"] + "|" + job["company"]).lower())
