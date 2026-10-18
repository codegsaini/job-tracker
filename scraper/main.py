"""Fetch jobs from every enabled source, filter, dedupe, and write docs/jobs.json."""
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

try:  # use the OS certificate store when available (fixes SSL errors on some machines)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent))
from common import Matcher, fingerprint, iso, now_utc  # noqa: E402
from sources import SOURCES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.yml"
OUTPUT = ROOT / "docs" / "jobs.json"


def load_existing():
    try:
        return json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main(only=None):
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    matcher = Matcher(cfg)
    data = load_existing()
    jobs = {j["id"]: j for j in data.get("jobs", [])}
    fingerprints = {fingerprint(j) for j in jobs.values()}
    status = data.get("sources", {})
    now = now_utc()
    now_iso = iso(now)
    cutoff = iso(now - timedelta(days=cfg.get("max_age_days", 30)))

    for name, (fetch, label) in SOURCES.items():
        sc = (cfg.get("sources") or {}).get(name) or {}
        if not sc.get("enabled") or (only and name not in only):
            if not sc.get("enabled"):
                status.pop(name, None)
            continue
        prev = status.get(name) or {}
        last = prev.get("last_run") if prev.get("fetched") else None  # only throttle after a productive run
        interval = sc.get("min_interval_hours")
        if not only and interval and last and now - datetime.fromisoformat(last) < timedelta(hours=interval):
            print(f"[{name}] skipped (ran {last})")
            continue

        warnings = []
        ctx = {
            "keywords": cfg.get("keywords") or [""],
            "search_location": cfg.get("search_location", ""),
            "warn": lambda msg: (warnings.append(msg), print(f"  warn: {msg}")),
        }
        started = time.time()
        error = None
        try:
            raw = fetch(sc, ctx)
        except Exception as e:  # one broken source must not break the run
            raw, error = [], f"{type(e).__name__}: {e}"[:300]
            print(f"  error: {error}")

        matched = new = 0
        for job in raw:
            prefiltered = job.pop("prefiltered", False)
            if not job["title"] or not job["url"]:
                continue
            if not prefiltered and not matcher.ok(job):
                continue
            if job["posted"] and job["posted"] < cutoff:
                continue
            matched += 1
            if job["id"] in jobs:
                jobs[job["id"]]["last_seen"] = now_iso
                continue
            fp = fingerprint(job)
            if fp in fingerprints:
                continue
            fingerprints.add(fp)
            job["source_label"] = label
            job["first_seen"] = job["last_seen"] = now_iso
            jobs[job["id"]] = job
            new += 1

        status[name] = {
            "label": label, "last_run": now_iso, "ok": error is None, "error": error,
            "warnings": warnings[:10], "fetched": len(raw), "matched": matched, "new": new,
            "seconds": round(time.time() - started, 1),
        }
        print(f"[{name}] fetched={len(raw)} matched={matched} new={new} ({status[name]['seconds']}s)")

    kept = [j for j in jobs.values() if (j.get("posted") or j["first_seen"]) >= cutoff]
    kept.sort(key=lambda j: (j["first_seen"], j.get("posted") or ""), reverse=True)

    OUTPUT.write_text(json.dumps(
        {"updated": now_iso, "sources": status, "jobs": kept},
        ensure_ascii=False, indent=0,
    ), encoding="utf-8")
    print(f"Wrote {len(kept)} jobs ({len(jobs) - len(kept)} expired) to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    # Optional: `python scraper/main.py lever amazon` runs only those sources.
    main(set(sys.argv[1:]) or None)
