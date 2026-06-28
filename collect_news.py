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
        for title, url in links:
            clean_url = make_absolute(url, "https://www.ithome.com.tw")
            if "?page=" in clean_url:
                continue
            if len(title) < 15:
                continue
            security_items.append({
                "title": clean_title(title),
                "url": clean_url,
                "source": "iThome"
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
                "source": "資安人"
            })
            count += 1
            if count >= 10:
                break
        print(f"    資安人: {count} items")

    save_json("security", security_items)

    # === AI ===
    print("  AI:")
    ai_items = []

    # DeepLearning.ai — find the latest weekly issue link, then scrape it
    print("    Fetching DeepLearning.ai The Batch...")
    html = fetch_url("https://www.deeplearning.ai/the-batch/")
    if html:
        # Find the first "Read the Issue" or link to a specific issue article
        issue_links = re.findall(r'href="(/the-batch/[^"#?]+)"', html)
        # Filter out the main /the-batch/ page link, find actual article links
        articles = [l for l in issue_links if l != "/the-batch/" and l != "/the-batch"]
        # Also look for article cards
        article_matches = re.findall(r'href="(https?://www\.deeplearning\.ai/the-batch/[^"#?]+)"', html)
        articles.extend([a for a in article_matches if a not in articles])
        
        issue_url = articles[0] if articles else None
        
        if issue_url:
            print(f"      Found latest issue: {issue_url}")
            issue_html = fetch_url(issue_url)
            if issue_html:
                links = extract_links(issue_html, min_len=15)
                dl_count = 0
                for title, url in links:
                    clean = make_absolute(url, "https://www.deeplearning.ai")
                    title_clean = clean_title(title)
                    # Skip navigation/header/footer
                    if any(skip in title_clean.lower() for skip in ["subscribe", "sign up", "newsletter", "archive", "search", "the batch"]):
                        continue
                    ai_items.append({
                        "title": title_clean,
                        "url": clean,
                        "source": "DeepLearning.ai"
                    })
                    dl_count += 1
                    if dl_count >= 15:
                        break
                print(f"      DeepLearning.ai: {dl_count} items")
            else:
                print(f"      Failed to fetch issue page")
        else:
            print(f"      No issue link found, falling back to page links")
            links = extract_links(html, min_len=20)
            dl_count = 0
            for title, url in links:
                ai_items.append({
                    "title": clean_title(title),
                    "url": make_absolute(url, "https://www.deeplearning.ai"),
                    "source": "DeepLearning.ai"
                })
                dl_count += 1
                if dl_count >= 10:
                    break
            print(f"      DeepLearning.ai (fallback): {dl_count} items")

    # Hacker News — front page is the "hot/active" stories (ranked by algorithm)
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
                "source": "Hacker News"
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
                "source": "SRE Weekly"
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
        # Parse repo article blocks
        # Each trending repo has a structure like:
        # <h2><a href="/owner/repo">owner / repo</a></h2>
        # <p>description</p>
        # <span>language</span>
        repo_pattern = re.compile(
            r'<h2[^>]*>\s*<a[^>]*href="(/\w[^"]+)"[^>]*>([^<]+)</a>',
            re.IGNORECASE
        )
        desc_pattern = re.compile(
            r'<p[^>]*class="col-9[^"]*"[^>]*>\s*(.+?)\s*</p>',
            re.IGNORECASE | re.DOTALL
        )
        lang_pattern = re.compile(
            r'<span[^>]*itemprop="programmingLanguage"[^>]*>([^<]+)</span>',
            re.IGNORECASE
        )

        # Get all descriptions and languages
        descriptions = [clean_title(m.group(1)) for m in desc_pattern.finditer(html)]
        languages = [m.group(1).strip() for m in lang_pattern.finditer(html)]
        
        repo_count = 0
        for m in repo_pattern.finditer(html):
            repo_path = m.group(1).strip()
            title = m.group(2).strip().replace('\n', '').replace('  ', ' ')
            if repo_path.count("/") == 2:
                desc = descriptions[repo_count] if repo_count < len(descriptions) else ""
                lang = languages[repo_count] if repo_count < len(languages) else ""
                trending_items.append({
                    "title": title.strip(),
                    "url": f"https://github.com{repo_path}",
                    "description": desc[:300],
                    "language": lang,
                    "source": "GitHub Trending"
                })
                repo_count += 1
                if repo_count >= 25:
                    break
        print(f"    GitHub Trending: {repo_count} items")

    save_json("trending", trending_items)

    print("Done!")

if __name__ == "__main__":
    main()