#!/usr/bin/env python3
"""
Daily news collector for /home/dieno/mynews
分類: Security, AI, SRE
Output: data/security.json, data/ai.json, data/sre.json
"""

import json
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("/home/dieno/mynews/data")

def fetch_url(url, timeout=15):
    """Fetch a URL and return text content."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--connect-timeout", "10", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout+5
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except Exception as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
    return ""

def extract_links(html, url_pattern=None, min_len=5):
    """Extract (title, url) pairs from HTML."""
    items = []
    # Match <a ... href="..." ...>TITLE</a>
    pattern = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', re.IGNORECASE | re.DOTALL)
    for m in pattern.finditer(html):
        url = m.group(1).strip()
        title = m.group(2).strip()
        title = re.sub(r'<[^>]+>', '', title)  # strip inner HTML
        if not title or len(title) < min_len:
            continue
        if url.startswith("#") or url.startswith("javascript:"):
            continue
        if url_pattern and url_pattern not in url:
            continue
        items.append((title, url))
    return items

def clean_title(title):
    """Clean up a title string."""
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.replace('&#x27;', "'").replace('&amp;', '&').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
    return title[:150]

def make_absolute(url, base):
    """Convert relative URL to absolute."""
    if url.startswith("http"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        base_domain = re.match(r'(https?://[^/]+)', base)
        if base_domain:
            return base_domain.group(1) + url
    return base.rstrip("/") + "/" + url.lstrip("/")

def save_json(category, items):
    """Save items to JSON file."""
    filepath = DATA_DIR / f"{category}.json"
    data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "category": category.capitalize(),
        "items": items
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(items)} items to {filepath.name}")

def main():
    print(f"[{datetime.now().strftime('%H:%M')}] Collecting news...")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # === Security ===
    print("  Security:")
    security_items = []

    print("    Fetching iThome (資安)...")
    html = fetch_url("https://www.ithome.com.tw/security")
    if html:
        links = extract_links(html, min_len=10)
        for title, url in links:
            security_items.append({
                "title": clean_title(title),
                "url": make_absolute(url, "https://www.ithome.com.tw"),
                "source": "iThome"
            })
            if len(security_items) >= 15:
                break
        print(f"    iThome: {len(security_items)} items")

    print("    Fetching 資安人...")
    html = fetch_url("https://www.secumanager.com/")
    if html:
        links = extract_links(html, min_len=10)
        secumanager_count = 0
        for title, url in links:
            security_items.append({
                "title": clean_title(title),
                "url": make_absolute(url, "https://www.secumanager.com"),
                "source": "資安人"
            })
            secumanager_count += 1
            if secumanager_count >= 10:
                break
        print(f"    資安人: {secumanager_count} items")

    save_json("security", security_items)

    # === AI ===
    print("  AI:")
    ai_items = []

    print("    Fetching GitHub Trending...")
    html = fetch_url("https://github.com/trending")
    if html:
        gh_pattern = re.compile(r'<h[23][^>]*>\s*<a[^>]*href="(/\w[^"]+)"[^>]*>([^<]+)</a>', re.IGNORECASE)
        for m in gh_pattern.finditer(html):
            repo_path = m.group(1).strip()
            title = m.group(2).strip()
            if repo_path.count("/") == 2:
                ai_items.append({
                    "title": f"{title.strip('/')}",
                    "url": f"https://github.com{repo_path}",
                    "source": "GitHub Trending"
                })
                if len([x for x in ai_items if x["source"] == "GitHub Trending"]) >= 15:
                    break
        print(f"    GitHub Trending: {len([x for x in ai_items if x['source'] == 'GitHub Trending'])} items")

    print("    Fetching DeepLearning.ai...")
    html = fetch_url("https://www.deeplearning.ai/the-batch/")
    if html:
        links = extract_links(html, min_len=15)
        dl_count = 0
        for title, url in links:
            title_lower = title.lower()
            if any(kw in title_lower for kw in ["ai", "model", "learning", "neural", "gpt", "llm", "machine", "data", "robot", "compute", "gpu", "research"]):
                ai_items.append({
                    "title": clean_title(title),
                    "url": make_absolute(url, "https://www.deeplearning.ai"),
                    "source": "DeepLearning.ai"
                })
                dl_count += 1
                if dl_count >= 10:
                    break
        print(f"    DeepLearning.ai: {dl_count} items")

    print("    Fetching Hacker News...")
    html = fetch_url("https://news.ycombinator.com/")
    if html:
        hn_pattern = re.compile(r'class="titleline"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)', re.IGNORECASE)
        hn_count = 0
        for m in hn_pattern.finditer(html):
            url = m.group(1).strip()
            title = m.group(2).strip()
            if url.startswith("item?"):
                url = f"https://news.ycombinator.com/{url}"
            ai_items.append({
                "title": clean_title(title),
                "url": url,
                "source": "Hacker News"
            })
            hn_count += 1
            if hn_count >= 20:
                break
        print(f"    Hacker News: {hn_count} items")

    print(f"    Total AI: {len(ai_items)} items")
    save_json("ai", ai_items)

    # === SRE ===
    print("  SRE:")
    sre_items = []

    print("    Fetching SRE Weekly...")
    html = fetch_url("https://sreweekly.com/")
    if html:
        links = extract_links(html, min_len=15)
        for title, url in links:
            # Skip navigation/social links
            if any(skip in url for skip in ["sreweekly.com/category", "sreweekly.com/tag", "twitter.com", "facebook.com", "linkedin.com"]):
                continue
            if any(skip in title.lower() for skip in ["subscribe", "archives", "search", "login"]):
                continue
            sre_items.append({
                "title": clean_title(title),
                "url": make_absolute(url, "https://sreweekly.com"),
                "source": "SRE Weekly"
            })
            if len(sre_items) >= 30:
                break
        print(f"    SRE Weekly: {len(sre_items)} items")

    save_json("sre", sre_items)

    print("Done!")

if __name__ == "__main__":
    main()