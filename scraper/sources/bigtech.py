"""Big-tech career sites with their own (undocumented but public) search APIs."""
import time
from datetime import datetime

from common import get, make_job


def amazon(sc, ctx):
    jobs = []
    for kw in ctx["keywords"]:
        data = get("https://www.amazon.jobs/en/search.json", params={
            "base_query": kw, "loc_query": ctx["search_location"],
            "result_limit": 100, "sort": "recent",
        }).json()
        for j in data.get("jobs", []):
            try:
                posted = datetime.strptime(" ".join(j["posted_date"].split()), "%B %d, %Y")
            except (KeyError, ValueError):
                posted = None
            jobs.append(make_job(
                "amazon", j["id_icims"], j["title"], "Amazon",
                j.get("normalized_location") or j.get("location"),
                "https://www.amazon.jobs" + j["job_path"], posted=posted,
            ))
    return jobs


def microsoft(sc, ctx):
    jobs = []
    base = "https://apply.careers.microsoft.com"
    get(f"{base}/careers", headers={"Accept": "text/html"})  # sets the session cookies the API wants
    for kw in ctx["keywords"]:
        for page in range(sc.get("pages", 3)):
            data = get(f"{base}/api/pcsx/search", params={
                "domain": "microsoft.com", "query": kw, "location": ctx["search_location"],
                "start": page * 10, "sort_by": "timestamp",
            }, headers={"Referer": f"{base}/careers"}).json()
            positions = (data.get("data") or {}).get("positions") or []
            for j in positions:
                url = j.get("positionUrl") or f"/careers/job/{j['id']}"
                jobs.append(make_job(
                    "microsoft", j["id"], j["name"], "Microsoft",
                    "; ".join(j.get("locations") or []),
                    url if url.startswith("http") else base + url, posted=j.get("postedTs"),
                ))
            time.sleep(sc.get("delay_seconds", 2))
            if len(positions) < 10:
                break
    return jobs
