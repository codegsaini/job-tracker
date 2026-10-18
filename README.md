# 💼 Job Tracker

Scrapes IT jobs from MNC career sites and job boards every 6 hours with GitHub
Actions, filters them by your keywords and locations, and publishes a searchable
page on GitHub Pages. Everything runs on free tiers. You don't need a server or a database.

```
config.yml ──► scraper/main.py (GitHub Actions, every 6h) ──► docs/jobs.json ──► docs/index.html (GitHub Pages)
```

## Sources

| Source | Covers | Needs |
|---|---|---|
| Workday | NVIDIA, Salesforce, Accenture, Intel, Adobe, PwC, Mastercard, HP, Micron, Citi, Morgan Stanley, Barclays, Qualcomm | – |
| Greenhouse / Lever / SmartRecruiters | Stripe, Databricks, Cloudflare, MongoDB, Okta, ServiceNow, Bosch, Meesho, Paytm… | – |
| Amazon, Microsoft | Their own career APIs | – |
| LinkedIn | Public guest search (unofficial, may get blocked) | – |
| Email alerts | Your LinkedIn and Naukri job-alert emails | `EMAIL_USER`, `EMAIL_PASSWORD` secrets |
| Google Jobs (JSearch) | Naukri, Indeed, LinkedIn… through Google for Jobs | `RAPIDAPI_KEY` secret |

Add a company by appending its careers URL or slug under the right section in
`config.yml`. Workday URLs look like `https://<tenant>.wd<N>.myworkdayjobs.com/<site>`.

## Setup

1. Push this folder to a **public** GitHub repo.
2. **Settings → Pages → Build and deployment**: Source *Deploy from a branch*, branch `main`, folder `/docs`.
3. **Settings → Actions → General → Workflow permissions**: *Read and write*.
4. **Actions → Scrape jobs → Run workflow** to do the first run.
5. Open `https://<user>.github.io/<repo>/`.

### Optional: Naukri and LinkedIn email alerts
1. Create job alerts on naukri.com and linkedin.com (you can use a dedicated Gmail account).
2. In Gmail, turn on 2-step verification, then create an **App Password** (Google Account → Security → App passwords).
3. Add the repo secrets `EMAIL_USER` (the address) and `EMAIL_PASSWORD` (the app password) under **Settings → Secrets and variables → Actions**.

### Optional: Google Jobs (JSearch)
Subscribe to the free plan of [JSearch on RapidAPI](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
and add your key as the `RAPIDAPI_KEY` secret. By default it runs once a day with 5 queries,
which stays within the free quota.

## Browser alerts
Click **🔔 Enable alerts** on the page. While the tab is open, the page checks for new data
every 10 minutes and shows a desktop notification when new jobs arrive. Jobs found since
your last **Mark all seen** get a green **NEW** badge.

## Run locally
```
pip install -r requirements.txt
python scraper/main.py              # all sources
python scraper/main.py lever amazon # only some sources
python -m http.server -d docs       # then open http://localhost:8000
```

## Notes
- Jobs are removed 30 days after they were posted, or after they were first seen if the source gives no date (`max_age_days`).
- GitHub disables scheduled workflows in repos with no activity for 60 days. The bot's
  data commits normally keep the repo active. If the workflow ever gets disabled, re-enable it in the Actions tab.
- Naukri's own API now requires a captcha, so Naukri jobs come from email alerts and Google Jobs.
