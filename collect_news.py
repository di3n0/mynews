#!/usr/bin/env python3
"""
Daily news collector for /home/dieno/mynews
分類: Security, AI, SRE, Trending
Output: data/security.json, data/ai.json, data/sre.json, data/trending.json
"""

import json
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("/home/dieno/mynews/data")

def fetch_url(url, timeout=20):
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

def extract_links(html, min_len=5):
    items = []
    pattern = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', re.IGNORECASE | re.DOTALL)
    for m in pattern.finditer(html):
        url = m.group(1).strip()
        title = m.group(2).strip()
        title = re.sub(r'<[^>]+>', '', title)
        if not title or len(title) < min_len:
            continue
        if url.startswith("#") or url.startswith("javascript:"):
            continue
        items.append((title, url))
    return items

def clean_title(title):
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.replace('&#x27;', "'").replace('&amp;', '&').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
    return title[:200]

def make_absolute(url, base):
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

    # === Security ===
    print("  Security:")
    security_items = []

    print("    Fetching iThome...")
    html = fetch_url("https://www.ithome.com.tw/")
    if html:
        links = extract_links(html, min_len=10)
        seen = set()
        for title, url in links:
            clean_url = make_absolute(url, "https://www.ithome.com.tw")
            if "?page=" in clean_url or clean_url in seen:
                continue
            seen.add(clean_url)
            if len(title) < 15:
                continue
            security_items.append({
                "title": clean_title(title),
                "url": clean_url,
                "source": "iThome",
                "site": "ithome.com.tw"
            })
            if len(security_items) >= 15:
                break
        print(f"    iThome: {len(security_items)} items")

    print("    Fetching 資安人...")
    html = fetch_url("https://www.informationsecurity.com.tw/main/index.aspx")
    if html:
        links = extract_links(html, min_len=10)
        count = 0
        seen_urls = set()
        for title, url in links:
            clean_url = make_absolute(url, "https://www.informationsecurity.com.tw")
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            if len(clean_url) < 30 or "?" in clean_url:
                continue
            security_items.append({
                "title": clean_title(title),
                "url": clean_url,
                "source": "資安人",
                "site": "informationsecurity.com.tw"
            })
            count += 1
            if count >= 10:
                break
        print(f"    資安人: {count} items")

    save_json("security", security_items)

    # === AI ===
    print("  AI:")
    ai_items = []

    # DeepLearning.ai — scrape the /the-batch page directly for articles
    print("    Fetching DeepLearning.ai The Batch...")
    html = fetch_url("https://www.deeplearning.ai/the-batch/")
    if html:
        links = extract_links(html, min_len=20)
        dl_count = 0
        for title, url in links:
            clean = make_absolute(url, "https://www.deeplearning.ai")
            title_clean = clean_title(title)
            ai_items.append({
                "title": title_clean,
                "url": clean,
                "source": "DeepLearning.ai",
                "site": "deeplearning.ai"
            })
            dl_count += 1
            if dl_count >= 15:
                break
        print(f"    DeepLearning.ai: {dl_count} items")

    # Hacker News — front page is the "hot/active" stories
    print("    Fetching Hacker News (hot)...")
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
                "source": "Hacker News",
                "site": "news.ycombinator.com"
            })
            hn_count += 1
            if hn_count >= 25:
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
            if any(skip in url for skip in ["sreweekly.com/category", "sreweekly.com/tag", "twitter.com", "facebook.com", "linkedin.com"]):
                continue
            if any(skip in title.lower() for skip in ["subscribe", "archives", "search", "login"]):
                continue
            sre_items.append({
                "title": clean_title(title),
                "url": make_absolute(url, "https://sreweekly.com"),
                "source": "SRE Weekly",
                "site": "sreweekly.com"
            })
            if len(sre_items) >= 30:
                break
        print(f"    SRE Weekly: {len(sre_items)} items")

    save_json("sre", sre_items)

    # === GitHub Trending ===
    print("  Trending:")
    trending_items = []

    print("    Fetching GitHub Trending...")
    html = fetch_url("https://github.com/trending")
    if html:
        # Use a simpler approach: find all article blocks
        # Split by <article class="Box-row">
        articles_raw = re.split(r'<article\s+class="Box-row"[^>]*>', html, flags=re.IGNORECASE)
        print(f"    Found {len(articles_raw)-1} article blocks")

        for article_html in articles_raw[1:]:  # skip first split part
            # Extract repo name from h2 > a
            repo_match = re.search(r'href="(/\w[^"/]+/[^"#?]+)"', article_html)
            if not repo_match:
                continue
            repo_path = repo_match.group(1)
            if repo_path.count("/") != 2:
                continue

            # Clean repo name
            repo_name = repo_path.strip("/")

            # Extract description
            desc_match = re.search(r'<p[^>]*class="col-9[^"]*"[^>]*>\s*(.*?)\s*</p>', article_html, re.DOTALL)
            description = clean_title(desc_match.group(1)) if desc_match else ""

            # Extract language
            lang_match = re.search(r'<span[^>]*itemprop="programmingLanguage"[^>]*>([^<]+)</span>', article_html)
            language = lang_match.group(1).strip() if lang_match else ""

            # Extract stars
            stars_match = re.search(r'Octicon[^>]*star[^>]*</svg>\s*([\d,]+)', article_html)
            stars = stars_match.group(1).strip() if stars_match else ""

            # Extract forks
            forks_match = re.search(r'Octicon[^>]*repo[-]forked[^>]*</svg>\s*([\d,]+)', article_html)
            forks = forks_match.group(1).strip() if forks_match else ""

            # Extract today stars
            today_match = re.search(r'([\d,]+)\s+stars\s+today', article_html, re.IGNORECASE)
            today_stars = today_match.group(1).strip() if today_match else ""

            # Build description with details
            full_desc = description
            details_parts = []
            if stars:
                details_parts.append(f"⭐ {stars} stars")
            if forks:
                details_parts.append(f"⑂ {forks} forks")
            if today_stars:
                details_parts.append(f"📈 {today_stars} today")
            if details_parts:
                extra = " · ".join(details_parts)
                if full_desc:
                    full_desc = f"{full_desc}\n({extra})"
                else:
                    full_desc = extra

            trending_items.append({
                "title": repo_name,
                "url": f"https://github.com{repo_path}",
                "description": full_desc[:300],
                "language": language,
                "source": "GitHub Trending",
                "site": "github.com/trending"
            })

            if len(trending_items) >= 25:
                break

        print(f"    GitHub Trending: {len(trending_items)} items")

    save_json("trending", trending_items)

    print("Done!")

if __name__ == "__main__":
    main()