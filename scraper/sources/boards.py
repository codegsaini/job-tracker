"""Job boards and aggregators."""
import os
import time

from bs4 import BeautifulSoup

from common import get, make_job


def linkedin(sc, ctx):
    """LinkedIn's logged-out ("guest") jobs search. Unofficial; may be rate-limited."""
    jobs = []
    seconds = int(sc.get("time_range_hours", 24)) * 3600
    for kw in ctx["keywords"]:
        for page in range(sc.get("pages", 2)):
            r = get(
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                params={"keywords": kw, "location": ctx["search_location"],
                        "f_TPR": f"r{seconds}", "start": page * 25},
                headers={"Accept": "text/html"},
            )
            cards = BeautifulSoup(r.text, "html.parser").select("div.base-search-card")
            for c in cards:
                urn = c.get("data-entity-urn", "")
                job_id = urn.rsplit(":", 1)[-1]
                title = c.select_one(".base-search-card__title")
                if not job_id or not title:
                    continue
                company = c.select_one(".base-search-card__subtitle")
                location = c.select_one(".job-search-card__location")
                posted = c.select_one("time")
                jobs.append(make_job(
                    "linkedin", job_id, title.get_text(),
                    company.get_text() if company else "",
                    location.get_text() if location else "",
                    f"https://www.linkedin.com/jobs/view/{job_id}",
                    posted=posted.get("datetime") if posted else None,
                ))
            time.sleep(sc.get("delay_seconds", 2))
            if len(cards) < 25:
                break
    return jobs


def jsearch(sc, ctx):
    """Google for Jobs via RapidAPI JSearch (includes Naukri, LinkedIn, Indeed, ...)."""
    key = os.environ.get("RAPIDAPI_KEY")
    if not key:
        ctx["warn"]("jsearch: RAPIDAPI_KEY not set, skipped")
        return []
    jobs = []
    for q in sc.get("queries") or []:
        data = get("https://jsearch.p.rapidapi.com/search", params={
            "query": q, "page": 1, "num_pages": 1, "date_posted": sc.get("date_posted", "week"),
        }, headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}).json()
        for j in data.get("data") or []:
            location = ", ".join(x for x in (j.get("job_city"), j.get("job_state"), j.get("job_country")) if x)
            jobs.append(make_job(
                "jsearch", j["job_id"], j["job_title"], j.get("employer_name"), location,
                j.get("job_apply_link"), posted=j.get("job_posted_at_datetime_utc"),
                remote=j.get("job_is_remote"), via=j.get("job_publisher"),
            ))
    return jobs


def remotive(sc, ctx):
    data = get("https://remotive.com/api/remote-jobs", params={"category": "software-dev"}).json()
    return [
        make_job("remotive", j["id"], j["title"], j["company_name"],
                 "Remote - " + (j.get("candidate_required_location") or ""), j["url"],
                 posted=j.get("publication_date"), remote=True)
        for j in data.get("jobs", [])
    ]


def remoteok(sc, ctx):
    data = get("https://remoteok.com/api").json()
    return [
        make_job("remoteok", j["id"], j["position"], j["company"],
                 "Remote - " + (j.get("location") or ""), j["url"],
                 posted=j.get("date"), remote=True)
        for j in data if isinstance(j, dict) and "position" in j
    ]
