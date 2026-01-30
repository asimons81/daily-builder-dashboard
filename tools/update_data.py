import json
import os
import requests
from datetime import datetime, timezone

OWNER = os.environ.get("GITHUB_OWNER", "asimons81")
TOKEN = os.environ.get("GITHUB_TOKEN")
API = "https://api.github.com"

headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}


def utc_day_start():
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def get_repos():
    repos = []
    page = 1
    while True:
        r = requests.get(f"{API}/users/{OWNER}/repos", params={"per_page": 100, "page": page, "sort": "updated"}, headers=headers)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        repos.extend([repo["name"] for repo in data])
        page += 1
    return repos


def count_commits(repo, since_iso):
    r = requests.get(f"{API}/repos/{OWNER}/{repo}/commits", params={"since": since_iso, "per_page": 100}, headers=headers)
    r.raise_for_status()
    return len(r.json())


def main():
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN required")

    since = utc_day_start().isoformat()
    repos = get_repos()

    total_commits = 0
    repos_with_commits = 0

    for repo in repos:
        try:
            c = count_commits(repo, since)
        except requests.HTTPError:
            continue
        if c > 0:
            repos_with_commits += 1
            total_commits += c

    # load data.json
    data_path = os.path.join(os.path.dirname(__file__), "..", "data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data.setdefault("shipping", {})
    data["shipping"]["ships"] = repos_with_commits
    data["shipping"]["commit_count"] = total_commits
    data["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
