import json
import os
import subprocess
import requests
from datetime import datetime, timezone

# Load .env manually if needed, or assume environment is set
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

load_env()

OWNER = os.environ.get("GITHUB_OWNER", "asimons81")
TOKEN = os.environ.get("GITHUB_TOKEN")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
CT0 = os.environ.get("CT0")
X_HANDLE = "tonysimons_"
API = "https://api.github.com"

headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

def get_x_followers():
    if not AUTH_TOKEN or not CT0:
        return None
    try:
        # Use bird to get user tweets and extract follower count from JSON-full
        cmd = ["bird", "user-tweets", X_HANDLE, "-n", "1", "--json-full"]
        env = os.environ.copy()
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data and len(data) > 0:
                # Look for followers_count in the raw user data
                user_res = data[0].get("_raw", {}).get("core", {}).get("user_results", {}).get("result", {})
                legacy = user_res.get("legacy", {})
                count = legacy.get("followers_count")
                if count is not None:
                    return count
    except Exception as e:
        print(f"X fetch error: {e}")
    return None

def get_repos():
    repos = []
    page = 1
    while True:
        try:
            r = requests.get(f"{API}/users/{OWNER}/repos", params={"per_page": 100, "page": page, "sort": "updated"}, headers=headers)
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            repos.extend([{"name": repo["name"], "updated_at": repo["updated_at"]} for repo in data])
            page += 1
        except Exception as e:
            print(f"GitHub fetch error: {e}")
            break
    return repos

def count_commits(repo, since_iso):
    try:
        r = requests.get(f"{API}/repos/{OWNER}/{repo}/commits", params={"since": since_iso, "per_page": 100}, headers=headers)
        r.raise_for_status()
        return len(r.json())
    except:
        return 0

def main():
    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    all_repos = get_repos()

    total_commits = 0
    repos_with_commits = 0
    project_pulse = []

    for repo in all_repos:
        name = repo["name"]
        c = count_commits(name, since) if TOKEN else 0
        
        status = "Idle"
        if c > 0:
            repos_with_commits += 1
            total_commits += c
            status = f"{c} commits today"
        else:
            updated_at = datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - updated_at).days
            if days_ago < 7:
                status = f"Active {days_ago}d ago"

        project_pulse.append({"name": name, "status": status})

    x_followers = get_x_followers()

    # load data.json
    data_path = os.path.join(os.path.dirname(__file__), "..", "data.json")
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    data["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    if "shipping" not in data: data["shipping"] = {}
    data["shipping"]["ships"] = repos_with_commits
    data["shipping"]["commit_count"] = total_commits
    
    if x_followers is not None:
        if "content_machine" not in data: data["content_machine"] = {}
        data["content_machine"]["x_followers"] = x_followers

    data["projects"] = project_pulse

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"Update complete: {x_followers} followers, {total_commits} commits.")

if __name__ == "__main__":
    main()
