"""
UK SDET/QA Job Alert
--------------------
Queries the Adzuna Jobs API for SDET / QA Engineer roles in the UK,
compares against previously seen job IDs (stored in seen_jobs.json),
and sends a Telegram message for each newly discovered listing.

Required environment variables (set as GitHub Actions secrets):
  ADZUNA_APP_ID
  ADZUNA_APP_KEY
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""

import os
import json
import time
import requests

ADZUNA_APP_ID = os.environ["ADZUNA_APP_ID"]
ADZUNA_APP_KEY = os.environ["ADZUNA_APP_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SEEN_JOBS_FILE = "seen_jobs.json"
COUNTRY = "gb"  # Adzuna's code for the UK

# Search terms to cover — feel free to add/remove
SEARCH_QUERIES = [
    "SDET",
    "QA Engineer",
    "Quality Assurance Engineer",
    "Test Automation Engineer",
    "QA Automation Engineer",
]

RESULTS_PER_PAGE = 50


def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_jobs(seen_ids):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(sorted(seen_ids), f)


def fetch_jobs(query):
    url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": RESULTS_PER_PAGE,
        "what": query,
        "content-type": "application/json",
        "sort_by": "date",
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("results", [])


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()


def format_job_message(job):
    title = job.get("title", "Untitled role")
    company = job.get("company", {}).get("display_name", "Unknown company")
    location = job.get("location", {}).get("display_name", "UK")
    url = job.get("redirect_url", "")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")

    salary_line = ""
    if salary_min and salary_max:
        salary_line = f"\n💰 £{int(salary_min):,} - £{int(salary_max):,}"

    return (
        f"🆕 <b>{title}</b>\n"
        f"🏢 {company}\n"
        f"📍 {location}"
        f"{salary_line}\n"
        f"🔗 {url}"
    )


def main():
    seen_ids = load_seen_jobs()
    new_seen_ids = set(seen_ids)
    new_jobs = []

    for query in SEARCH_QUERIES:
        try:
            jobs = fetch_jobs(query)
        except requests.RequestException as e:
            print(f"Failed to fetch jobs for query '{query}': {e}")
            continue

        for job in jobs:
            job_id = job.get("id")
            if not job_id:
                continue
            if job_id not in seen_ids:
                new_jobs.append(job)
                new_seen_ids.add(job_id)

        time.sleep(1)  # be polite to the API

    if not new_jobs:
        print("No new jobs found.")
    else:
        print(f"Found {len(new_jobs)} new job(s). Sending Telegram alerts...")
        for job in new_jobs:
            try:
                send_telegram_message(format_job_message(job))
                time.sleep(1)  # avoid Telegram rate limits
            except requests.RequestException as e:
                print(f"Failed to send Telegram message: {e}")

    save_seen_jobs(new_seen_ids)


if __name__ == "__main__":
    main()
