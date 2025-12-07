from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import psutil
import os

RESULT_FILE = 'threaded_results.txt'
BASE = 'https://dental-first.ru/catalog/'
LINK_LIMIT = 50  # одинаковый лимит для всех серверов

# Удаляем старый файл результатов
if os.path.exists(RESULT_FILE):
    os.remove(RESULT_FILE)

app = Flask(__name__)
lock = threading.Lock()

def parse_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    results, page_sum = [], 0.0
    for card in soup.select('div.set-card'):
        title_tag = card.select_one('.set-card__title a')
        if not title_tag:
            continue
        name = title_tag.get_text(strip=True)
        price_tag = card.select_one('meta[itemprop="price"]') or card.select_one('.set-card__price')
        price = float(price_tag['content']) if price_tag and price_tag.has_attr('content') else 0.0
        results.append([name, price])
        page_sum += price
    return results, page_sum

def collect_product_links(category_url, limit=LINK_LIMIT):
    try:
        r = requests.get(category_url, headers={'User-Agent': 'local-bench/1.0'}, timeout=10)
        r.raise_for_status()
    except:
        return []
    soup = BeautifulSoup(r.text, 'lxml')
    links = []
    for a in soup.find_all('a', href=True):
        href = urljoin(BASE, a['href'])
        if href.startswith(category_url) and href not in links:
            links.append(href)
            if len(links) >= limit:
                break
    return links

def fetch_link(link):
    try:
        r = requests.get(link, headers={'User-Agent': 'local-bench/1.0'}, timeout=10)
        if r.status_code == 200:
            return parse_content(r.text)
    except:
        pass
    return [], 0.0

@app.route('/parse', methods=['GET'])
def parse_route():
    start = time.perf_counter()
    links = collect_product_links(BASE)
    titles, total_sum = [], 0.0
    seen = set()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_link, link) for link in links]
        for future in as_completed(futures):
            items, page_sum = future.result()
            for t, price in items:
                line = f"{t} | {price}"
                if line not in seen:
                    titles.append([t, price])
                    total_sum += price
                    seen.add(line)

    with lock:
        with open(RESULT_FILE, 'w', encoding='utf-8') as f:  # перезапись файла
            for t, price in titles:
                f.write(f"{t} | {price}\n")

    p = psutil.Process()
    return jsonify({
        'server': 'Threaded-Flask',
        'time_ms': (time.perf_counter() - start) * 1000,
        'mem_bytes': p.memory_info().rss,
        'cpu_percent': p.cpu_percent(interval=0.1),
        'count': len(titles),
        'sum': total_sum
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8085, threaded=True)
