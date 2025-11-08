import re
import requests
import concurrent.futures
from datetime import datetime, timezone
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def fetch_blocklist(url, session=None):
    session = session or requests.Session()
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

def parse_filter_list(content):
    rules = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith(('!', '#')):
            continue
        rules.append(line)
    return rules

def generate_filter(file_contents, is_mobile=False):
    rules = set()
    stats = {"total_rules": 0, "duplicates_removed": 0}
    
    for content in file_contents:
        if not content:
            continue
        for rule in parse_filter_list(content):
            if rule not in rules:
                rules.add(rule)
            else:
                stats["duplicates_removed"] += 1
    
    stats["total_rules"] = len(rules)
    sorted_rules = sorted(rules)
    header = generate_header(len(sorted_rules), stats, is_mobile)
    return '
'.join([header] + sorted_rules), stats

def generate_header(rule_count, stats, is_mobile=False):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
    list_type = "Mobile" if is_mobile else "Desktop"
    
    line1 = "# Title: Ghostnetic's Blocklist - " + list_type
    line2 = "# Description: Consolidated adblock filters (" + list_type + " version)"
    line3 = "# Last Modified: " + timestamp
    line4 = "# Total Rules: " + str(rule_count)
    line5 = "# Duplicates Removed: " + str(stats['duplicates_removed'])
    
    return line1 + "
" + line2 + "
" + line3 + "
" + line4 + "
" + line5

def build_blocklist(urls, filename, is_mobile=False):
    logging.info("Building " + filename + "...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        with requests.Session() as session:
            results = executor.map(lambda url: fetch_blocklist(url, session), urls)
    
    file_contents = [r for r in results if r]
    filter_content, stats = generate_filter(file_contents, is_mobile)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(filter_content)
    
    msg = filename + " generated: " + str(stats['total_rules']) + " rules, " + str(stats['duplicates_removed']) + " duplicates removed"
    logging.info(msg)

def main():
    with open('config.json') as f:
        config = json.load(f)
    
    desktop_urls = config.get('blocklist_urls_desktop', [])
    mobile_urls = config.get('blocklist_urls_mobile', [])
    
    if desktop_urls:
        build_blocklist(desktop_urls, 'blocklist_desktop.txt', is_mobile=False)
    if mobile_urls:
        build_blocklist(mobile_urls, 'blocklist_mobile.txt', is_mobile=True)
    
    if not desktop_urls and not mobile_urls:
        logging.error("No blocklist URLs found in config.json")

if __name__ == "__main__":
    main()
