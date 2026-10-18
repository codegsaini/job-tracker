"""LinkedIn / Naukri job-alert emails, read over IMAP.

Set up job alerts on both sites, then give the workflow an inbox to read via the
EMAIL_USER / EMAIL_PASSWORD secrets (for Gmail use an App Password).
"""
import email
import imaplib
import os
import re
from datetime import timedelta
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from common import make_job, now_utc

LINK_PATTERNS = {
    "linkedin": (re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(\d+)"),
                 "https://www.linkedin.com/jobs/view/{id}"),
    "naukri": (re.compile(r"naukri\.com/job-listings-[^?\s\"']*?-(\d{9,})"), None),
}


def _html_parts(msg):
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if payload:
                yield payload.decode(part.get_content_charset() or "utf-8", "replace")


def parse_alert(html, posted):
    """Extract jobs from an alert email. Each job link's text is usually
    "title / company / location" on separate lines."""
    found = {}
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        for site, (pattern, url_tpl) in LINK_PATTERNS.items():
            m = pattern.search(a["href"])
            if not m:
                continue
            lines = [s.strip() for s in a.get_text("\n").split("\n") if s.strip()]
            if not lines or len(lines[0]) < 4:
                continue
            key = (site, m.group(1))
            if key in found and len(found[key][1]) >= len(lines):
                continue
            url = url_tpl.format(id=m.group(1)) if url_tpl else a["href"].split("?")[0]
            found[key] = (url, lines)
    jobs = []
    for (site, job_id), (url, lines) in found.items():
        jobs.append(make_job(
            f"{site}-email", job_id, lines[0],
            lines[1] if len(lines) > 1 else "",
            lines[2] if len(lines) > 2 else "",
            url, posted=posted, prefiltered=True,
        ))
    return jobs


def email_alerts(sc, ctx):
    user, password = os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASSWORD")
    if not (user and password):
        ctx["warn"]("email_alerts: EMAIL_USER / EMAIL_PASSWORD not set, skipped")
        return []
    since = (now_utc() - timedelta(days=sc.get("days", 3))).strftime("%d-%b-%Y")
    jobs = []
    imap = imaplib.IMAP4_SSL(sc.get("imap_host", "imap.gmail.com"))
    try:
        imap.login(user, password)
        imap.select(f'"{sc.get("folder", "INBOX")}"', readonly=True)
        for sender in sc.get("senders") or []:
            _, ids = imap.search(None, f'(FROM "{sender}" SINCE {since})')
            for num in ids[0].split():
                _, msg_data = imap.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                try:
                    posted = parsedate_to_datetime(msg["Date"])
                except (TypeError, ValueError):
                    posted = None
                for html in _html_parts(msg):
                    jobs.extend(parse_alert(html, posted))
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    return jobs
