#!/usr/bin/env python3
"""
Camera #0 - Film Studio
Recording GitHub repositories as Screen Tests
"""

import os
import json
import random
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
import requests

# Factory credentials
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"

# Recording limits
MAX_SIZE_FULL_MB = 100
MAX_SIZE_SHALLOW_MB = 500


def get_trending_repos() -> list:
    """Fetch trending repositories from GitHub."""
    # GitHub doesn't have an official trending API, so we search recent popular repos
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    # Search for repos created/updated in last 7 days with most stars
    params = {
        "q": "stars:>50 pushed:>2025-10-26",
        "sort": "stars",
        "order": "desc",
        "per_page": 30
    }

    try:
        response = requests.get(f"{GITHUB_API}/search/repositories",
                              headers=headers, params=params, timeout=30)
        response.raise_for_status()
        items = response.json().get("items", [])
        return [parse_repo(item) for item in items[:25]]
    except Exception as e:
        print(f"⚠️  Trending search failed: {e}")
        return []


def get_classic_repos() -> list:
    """Get high-starred classic repositories."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    params = {
        "q": "stars:>10000",
        "sort": "stars",
        "order": "desc",
        "per_page": 100
    }

    try:
        response = requests.get(f"{GITHUB_API}/search/repositories",
                              headers=headers, params=params, timeout=30)
        response.raise_for_status()
        items = response.json().get("items", [])
        return [parse_repo(item) for item in items]
    except Exception as e:
        print(f"⚠️  Classic search failed: {e}")
        return []


def get_indie_repos() -> list:
    """Find hidden gems (100-1k stars)."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    params = {
        "q": "stars:100..1000 pushed:>2025-10-01",
        "sort": "updated",
        "order": "desc",
        "per_page": 50
    }

    try:
        response = requests.get(f"{GITHUB_API}/search/repositories",
                              headers=headers, params=params, timeout=30)
        response.raise_for_status()
        items = response.json().get("items", [])
        return [parse_repo(item) for item in items]
    except Exception as e:
        print(f"⚠️  Indie search failed: {e}")
        return []


def get_experimental_repos() -> list:
    """Find weird/experimental repositories."""
    keywords = ["awesome", "wtf", "experimental", "art", "useless", "weird", "fun"]
    keyword = random.choice(keywords)

    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    params = {
        "q": f"{keyword} in:name,description stars:>10",
        "sort": "updated",
        "order": "desc",
        "per_page": 30
    }

    try:
        response = requests.get(f"{GITHUB_API}/search/repositories",
                              headers=headers, params=params, timeout=30)
        response.raise_for_status()
        items = response.json().get("items", [])
        return [parse_repo(item) for item in items]
    except Exception as e:
        print(f"⚠️  Experimental search failed: {e}")
        return []


def parse_repo(item: dict) -> dict:
    """Parse GitHub API response into our format."""
    return {
        "full_name": item["full_name"],
        "url": item["html_url"],
        "clone_url": item["clone_url"],
        "stars": item["stargazers_count"],
        "language": item.get("language", "Unknown"),
        "size_kb": item["size"]
    }


def select_repository() -> tuple[dict, str]:
    """Select today's repository for recording."""
    strategy = random.choices(
        ['trending', 'classic', 'indie', 'experimental'],
        weights=[40, 30, 20, 10]
    )[0]

    print(f"🎲 Selection strategy: {strategy}")

    # Get pool based on strategy
    if strategy == 'trending':
        pool = get_trending_repos()
    elif strategy == 'classic':
        pool = get_classic_repos()
    elif strategy == 'indie':
        pool = get_indie_repos()
    else:  # experimental
        pool = get_experimental_repos()

    if not pool:
        print("⚠️  Pool empty, trying classics as backup")
        pool = get_classic_repos()
        strategy = "classic_backup"

    if not pool:
        raise RuntimeError("No repositories found in any category")

    # Select random from pool
    selected = random.choice(pool)
    return selected, strategy


def estimate_repo_size(repo_info: dict) -> int:
    """Estimate repository size in MB."""
    # GitHub API returns size in KB
    size_kb = repo_info.get("size_kb", 0)
    size_mb = size_kb / 1024
    return int(size_mb)


def clone_repository(repo_url: str, target_path: Path, method: str = "full") -> bool:
    """Clone the repository."""
    print(f"📹 Recording: {repo_url}")
    print(f"📼 Method: {method}")

    try:
        if method == "full":
            cmd = ["git", "clone", repo_url, str(target_path)]
        elif method == "shallow":
            cmd = ["git", "clone", "--depth", "1", repo_url, str(target_path)]
        else:  # readme_only
            # For very large repos, just create a trailer with metadata
            target_path.mkdir(parents=True, exist_ok=True)
            trailer_file = target_path / "TRAILER.txt"
            with open(trailer_file, 'w') as f:
                f.write(f"This repository was too large to record.\n")
                f.write(f"Original URL: {repo_url}\n")
                f.write(f"This is a trailer only.\n")
            return True

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0

    except Exception as e:
        print(f"❌ Recording failed: {e}")
        return False


def generate_metadata(repo_info: dict, reel_number: int, capture_info: dict) -> dict:
    """Generate .film metadata."""
    return {
        "reel_number": reel_number,
        "recorded": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "repository": repo_info,
        "capture": capture_info,
        "review": {
            "category": capture_info.get("strategy", "unknown"),
            "runtime": "Captured at a moment in time",
            "genre": repo_info.get("language", "Unknown"),
            "director_note": f"A {repo_info.get('language', 'code')} repository. {repo_info['stars']} stars."
        }
    }


def get_next_reel_number() -> int:
    """Get next reel number."""
    reels_dir = Path("reels")
    if not reels_dir.exists():
        return 0

    reels = list(reels_dir.glob("reel_*"))
    return len(reels)


def log_production(timestamp: str, reel_number: int, repo_name: str, reel_location: str, metadata: dict):
    """Write to the production log."""
    readme_file = Path("README.md")

    try:
        if readme_file.exists():
            with open(readme_file, 'r') as f:
                content = f.read()
        else:
            print("⚠️  Log book not found")
            return

        stars = metadata["repository"]["stars"]
        language = metadata["repository"]["language"]
        method = metadata["capture"]["method"]
        repo_url = metadata["repository"]["url"]

        # Format stars nicely
        if stars >= 1000:
            stars_display = f"{stars // 1000}k"
        else:
            stars_display = str(stars)

        # Update "Now Showing" section
        now_showing_marker = "## 🎥 Now Showing"
        if now_showing_marker in content:
            # Find the table and replace its content
            pattern = r'(## 🎥 Now Showing\s*\n\s*\| Reel \| Subject \| Genre \| Recorded \|\s*\n\s*\|[^\n]+\|\s*\n)\|[^\n]+\|'
            new_row = f"| #{reel_number} | [{repo_name}]({repo_url}) | {language} · ⭐ {stars_display} | {timestamp.split()[0]} |"
            content = re.sub(pattern, r'\1' + new_row, content)

        # Update "Film Archive" section
        log_marker = "## 📽️ Film Archive"
        if log_marker not in content:
            content += f"\n\n{log_marker}\n\n"
            content += "| Reel # | Timestamp | Repository | Status | Location |\n"
            content += "|--------|-----------|------------|--------|----------|\n"

        status = f"✅ {method} ({stars}⭐ {language})"
        repo_link = f"[{repo_name}]({repo_url})"
        entry = f"| {reel_number} | {timestamp} | {repo_link} | {status} | [{reel_location}]({reel_location}) |\n"

        content += entry

        with open(readme_file, 'w') as f:
            f.write(content)

        print(f"📝 Production logged")
    except Exception as e:
        print(f"⚠️  Failed to write log: {e}")


def record_film():
    """Main recording process."""
    print("🎬 Camera #0 starting...")

    # Get reel number
    reel_number = get_next_reel_number()
    print(f"🎞️ Reel #{reel_number}")

    # Select repository
    repo_info, strategy = select_repository()
    print(f"🎯 Selected: {repo_info['full_name']}")

    # Estimate size and choose method
    size_mb = estimate_repo_size(repo_info)

    if size_mb < MAX_SIZE_FULL_MB:
        method = "full"
    elif size_mb < MAX_SIZE_SHALLOW_MB:
        method = "shallow"
    else:
        method = "readme_only"

    # Prepare paths
    reels_dir = Path("reels")
    reels_dir.mkdir(exist_ok=True)

    repo_name_safe = repo_info['full_name'].replace('/', '-')
    reel_dir = reels_dir / f"reel_{reel_number:04d}_{repo_name_safe}"
    reel_dir.mkdir(exist_ok=True)

    # Record
    start_time = datetime.now()
    success = clone_repository(repo_info['clone_url'], reel_dir / "repo", method)
    duration = (datetime.now() - start_time).total_seconds()

    if not success:
        print("❌ Recording failed")
        return None

    # Generate metadata
    capture_info = {
        "strategy": strategy,
        "method": method,
        "size_mb": size_mb,
        "duration_seconds": duration
    }

    metadata = generate_metadata(repo_info, reel_number, capture_info)

    # Save .film file
    film_file = reel_dir / ".film"
    with open(film_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Film recorded: {reel_dir}")

    # Update README production log
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reel_location = f"reels/reel_{reel_number:04d}_{repo_name_safe}"
    log_production(timestamp, reel_number, repo_info['full_name'], reel_location, metadata)

    return reel_dir


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("⚠️  Warning: GITHUB_TOKEN not set (rate limits will apply)")

    # Retry strategy
    MAX_ATTEMPTS = 3
    success = False

    for attempt in range(MAX_ATTEMPTS):
        try:
            record_film()
            print("🎬 That's a wrap!")
            success = True
            break
        except KeyboardInterrupt:
            print("\n⏹️  Recording stopped by user")
            exit(0)
        except Exception as e:
            if attempt < MAX_ATTEMPTS - 1:
                wait_time = (attempt + 1) * 5
                print(f"\n⚠️  Attempt {attempt + 1}/{MAX_ATTEMPTS} failed: {e}")
                print(f"🔄 Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"\n❌ All attempts failed: {e}")
                import traceback
                traceback.print_exc()
                exit(1)

    if not success:
        exit(1)
