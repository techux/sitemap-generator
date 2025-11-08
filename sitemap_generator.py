import requests
from bs4 import BeautifulSoup
import time
import random
import html
import re
import os
from urllib.parse import urlparse, urlunparse, quote
from datetime import datetime, timezone

# =======================
# CONFIGURATION
# =======================
BASE_URL = "https://termux-tech.blogspot.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SitemapBot/1.0)"}
CRAWL_LIMIT = 2000  # safety cap

# =======================
# LOAD EXISTING CREATED DATES
# =======================
created_dates_file = "created_dates.txt"
created_dates = {}

if os.path.exists(created_dates_file):
    with open(created_dates_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                created_dates[parts[1]] = parts[0]

# =======================
# URL NORMALIZATION
# =======================
def clean_url(url):
    """Remove Blogger query params, fragments, and normalize URL."""
    url = url.strip()

    # Remove fragments (#)
    url = url.split("#")[0]

    # Remove ?m=1 (mobile)
    if "?m=1" in url:
        url = url.replace("?m=1", "")

    # Remove trailing slashes (except base)
    if url.endswith("/") and url != BASE_URL:
        url = url.rstrip("/")

    # Skip Blogger search pages and feeds
    if "/search" in url or "/feeds/" in url:
        return None

    # Ensure it starts with BASE_URL
    if not url.startswith(BASE_URL):
        return None

    # Properly encode any special chars (like + or spaces)
    parsed = urlparse(url)
    safe_path = quote(parsed.path)
    safe_query = quote(parsed.query, safe="/=&?+")
    normalized = urlunparse((parsed.scheme, parsed.netloc, safe_path, "", safe_query, ""))

    return normalized


# =======================
# SIMPLE CRAWLER
# =======================
def crawl_site(base_url):
    visited = set()
    to_visit = [base_url]

    while to_visit and len(visited) < CRAWL_LIMIT:
        url = to_visit.pop(0)
        cleaned = clean_url(url)
        if not cleaned or cleaned in visited:
            continue

        try:
            r = requests.get(cleaned, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue

            visited.add(cleaned)
            soup = BeautifulSoup(r.text, "html.parser")

            for a in soup.find_all("a", href=True):
                link = a["href"]

                # Convert relative links
                if link.startswith("/"):
                    link = base_url.rstrip("/") + link

                cleaned_link = clean_url(link)
                if cleaned_link and cleaned_link not in visited and cleaned_link not in to_visit:
                    to_visit.append(cleaned_link)

        except Exception as e:
            print("Error:", e)
            continue

    return sorted(visited)


# =======================
# HELPERS
# =======================
def iso_today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def changefreq_for(url):
    if re.search(r"/\d{4}/\d{2}/", url):
        return "daily"
    return "weekly"


# =======================
# GENERATE SITEMAP
# =======================
def generate_sitemap(urls):
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for url in urls:
        safe_url = html.escape(url, quote=True)

        # preserve created date
        if url not in created_dates:
            created_dates[url] = iso_today()
        created = created_dates[url]

        # manipulate lastmod to look recent
        lastmod = iso_today()
        priority = round(random.uniform(0.5, 1.0), 2)
        changefreq = changefreq_for(url)

        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{safe_url}</loc>")
        xml_lines.append(f"    <lastmod>{lastmod}</lastmod>")
        xml_lines.append(f"    <changefreq>{changefreq}</changefreq>")
        xml_lines.append(f"    <priority>{priority}</priority>")
        xml_lines.append("  </url>")

    xml_lines.append("</urlset>")

    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(xml_lines))

    # persist created dates
    with open(created_dates_file, "w", encoding="utf-8") as f:
        for url, date in created_dates.items():
            f.write(f"{date} {url}\n")

    print(f"✅ Generated sitemap.xml with {len(urls)} URLs")


# =======================
# MAIN
# =======================
if __name__ == "__main__":
    print(f"🌐 Crawling: {BASE_URL}")
    urls = crawl_site(BASE_URL)
    generate_sitemap(urls)
