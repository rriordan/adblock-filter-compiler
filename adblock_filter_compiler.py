import re
import requests
import concurrent.futures
from datetime import datetime, timezone
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def fetch_blocklist(url, session=None):
    """Fetch blocklist using optional session for potential reuse."""
    session = session or requests.Session()
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

def parse_filter_list(content):
    """Parse filter list while preserving all valid syntax."""
    rules = []
    for line in content.splitlines():
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith(('!', '#')):
            continue
        # Keep all valid adblock rules as-is
        rules.append(line)
    return rules

def generate_filter(file_contents, is_mobile=False):
    """Generate consolidated filter list."""
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
    """Generate blocklist header."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
    list_type = "Mobile" if is_mobile else "Desktop"
    return (
        f"# Title: Ghostnetic's Blocklist - {list_type}
"
        f"# Description: Consolidated adblock filters ({list_type} version)
"
        f"# Last Modified: {timestamp}
"
        f"# Total Rules: {rule_count}
"
        f"# Duplicates Removed: {stats['duplicates_removed']}
"
    )

def build_blocklist(urls, filename, is_mobile=False):
    """Build a blocklist from given URLs."""
    logging.info(f"Building {filename}...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        with requests.Session() as session:
            results = executor.map(lambda url: fetch_blocklist(url, session), urls)
    
    file_contents = [r for r in results if r]
    filter_content, stats = generate_filter(file_contents, is_mobile)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(filter_content)
    
    logging.info(
        f"{filename} generated: {stats['total_rules']} rules, "
        f"{stats['duplicates_removed']} duplicates removed"
    )

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
