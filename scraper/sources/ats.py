"""Company applicant-tracking systems with public JSON endpoints."""
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from common import days_ago, get, make_job, post


def greenhouse(sc, ctx):
    jobs = []
    for slug in sc.get("companies") or []:
        try:
            data = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs").json()
        except Exception as e:
            ctx["warn"](f"greenhouse/{slug}: {e}")
            continue
        for j in data.get("jobs", []):
            jobs.append(make_job(
                "greenhouse", j["id"], j["title"], j.get("company_name") or slug,
                (j.get("location") or {}).get("name"), j["absolute_url"],
                posted=j.get("first_published") or j.get("updated_at"),
            ))
    return jobs


def lever(sc, ctx):
    jobs = []
    for slug in sc.get("companies") or []:
        try:
            data = get(f"https://api.lever.co/v0/postings/{slug}?mode=json").json()
        except Exception as e:
            ctx["warn"](f"lever/{slug}: {e}")
            continue
        for j in data:
            cats = j.get("categories") or {}
            location = cats.get("location") or ", ".join(cats.get("allLocations") or [])
            jobs.append(make_job(
                "lever", j["id"], j["text"], slug.title(), location, j["hostedUrl"],
                posted=j.get("createdAt"),
                remote=j.get("workplaceType") == "remote" or None,
            ))
    return jobs


def smartrecruiters(sc, ctx):
    jobs = []
    for company in sc.get("companies") or []:
        for kw in ctx["keywords"]:
            try:
                data = get(
                    f"https://api.smartrecruiters.com/v1/companies/{company}/postings",
                    params={"q": kw, "limit": 100},
                ).json()
            except Exception as e:
                ctx["warn"](f"smartrecruiters/{company}: {e}")
                break
            for j in data.get("content", []):
                loc = j.get("location") or {}
                jobs.append(make_job(
                    "smartrecruiters", j["id"], j["name"],
                    (j.get("company") or {}).get("name") or company,
                    loc.get("fullLocation") or loc.get("city"),
                    f"https://jobs.smartrecruiters.com/{company}/{j['id']}",
                    posted=j.get("releasedDate"), remote=loc.get("remote") or None,
                ))
    return jobs


def _workday_posted(text):
    # "Posted Today" / "Posted Yesterday" / "Posted 5 Days Ago" / "Posted 30+ Days Ago"
    t = (text or "").lower()
    if "today" in t:
        return days_ago(0)
    if "yesterday" in t:
        return days_ago(1)
    m = re.search(r"(\d+)", t)
    return days_ago(int(m.group(1))) if m else None


def _workday_company(company, pages, ctx):
    jobs = []
    u = urlparse(company["url"])
    tenant = u.netloc.split(".")[0]
    parts = [p for p in u.path.split("/") if p and not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", p)]
    site = parts[0]
    api = f"https://{u.netloc}/wday/cxs/{tenant}/{site}/jobs"
    try:
        for kw in ctx["keywords"]:
            for page in range(pages):
                data = post(api, json={
                    "appliedFacets": {}, "limit": 20, "offset": page * 20,
                    "searchText": f"{kw} {ctx['search_location']}".strip(),
                }).json()
                postings = data.get("jobPostings") or []
                for j in postings:
                    if "externalPath" not in j:
                        continue
                    native = (j.get("bulletFields") or [j["externalPath"]])[0]
                    jobs.append(make_job(
                        "workday", f"{tenant}:{native}", j.get("title"), company["name"],
                        j.get("locationsText"), f"https://{u.netloc}/{site}{j['externalPath']}",
                        posted=_workday_posted(j.get("postedOn")),
                    ))
                if len(postings) < 20:
                    break
    except Exception as e:
        ctx["warn"](f"workday/{company['name']}: {e}")
    return jobs


def workday(sc, ctx):
    # Each company is a separate host, so query them in parallel.
    companies = sc.get("companies") or []
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(lambda c: _workday_company(c, sc.get("pages", 2), ctx), companies)
    return [j for jobs in results for j in jobs]
