import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import datetime
import random
import os
import xml.etree.ElementTree as ET

# --- CONFIG ---
START_URL = "https://termux-tech.blogspot.com/"
MAX_PAGES = 500
OUTPUT_FILE = "sitemap.xml"
CREATED_FILE = "created_dates.txt"  # persistent storage of original creation times
# ---------------

visited = set()
to_visit = [START_URL]
urls = []

def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.netloc == urlparse(START_URL).netloc and parsed.scheme in ("http", "https")

# --- Crawl ---
print(f"Starting crawl at {START_URL}")
while to_visit and len(visited) < MAX_PAGES:
    current_url = to_visit.pop(0)
    if current_url in visited:
        continue
    visited.add(current_url)
    try:
        res = requests.get(current_url, timeout=10)
        if res.status_code != 200:
            continue
        urls.append(current_url)
        soup = BeautifulSoup(res.text, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            link = urljoin(current_url, a_tag["href"])
            if is_valid_url(link) and link not in visited and link not in to_visit:
                to_visit.append(link)
        print(f"Crawled: {current_url}")
    except Exception as e:
        print(f"Error on {current_url}: {e}")

# --- Load or create persistent created date list ---
created_dates = {}
if os.path.exists(CREATED_FILE):
    with open(CREATED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                created_dates[parts[0]] = parts[1]

# --- Prepare new entries and update creation list ---
now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
for url in urls:
    if url not in created_dates:
        created_dates[url] = now

# --- Write back created date store ---
with open(CREATED_FILE, "w", encoding="utf-8") as f:
    for url, date in created_dates.items():
        f.write(f"{url} {date}\n")

# --- Generate sitemap ---
print("Generating sitemap.xml ...")
xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

for url in sorted(set(urls)):
    created = created_dates.get(url, now)
    # Manipulate lastmod: add random offset between 0 and 6 days
    offset_days = random.randint(0, 6)
    lastmod_date = (datetime.datetime.utcnow() - datetime.timedelta(days=offset_days))
    lastmod = lastmod_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Priority and frequency
    priority = round(random.uniform(0.5, 1.0), 2)
    changefreq = "weekly" if "/p/" in url else "daily"

    xml_content += (
        f"  <url>\n"
        f"    <loc>{url}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        f"    <changefreq>{changefreq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        f"  </url>\n"
    )

xml_content += "</urlset>"

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(xml_content)

print(f"✅ Generated {OUTPUT_FILE} with {len(urls)} URLs")
