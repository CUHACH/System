import asyncio
from aiohttp import web, ClientSession, TCPConnector
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import aiofiles
import os
import time
import psutil

RESULT_FILE = 'async_results.txt'
BASE = 'https://dental-first.ru/catalog/'
LINK_LIMIT = 50
MAX_PARALLEL_REQUESTS = 10


if os.path.exists(RESULT_FILE):
    os.remove(RESULT_FILE)

def parse_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    results, page_sum = [], 0.0
    for card in soup.select('div.set-card'):
        title_tag = card.select_one('.set-card__title a')
        if not title_tag:
            continue
        name = title_tag.get_text(strip=True)
        price_tag = card.select_one('meta[itemprop="price"]') or card.select_one('.set-card__price')
        try:
            price = float(price_tag['content']) if price_tag and price_tag.has_attr('content') else 0.0
        except:
            price = 0.0
        results.append([name, price])
        page_sum += price
    return results, page_sum

async def fetch(session, url):
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                print(f"Ошибка {resp.status} при запросе {url}")
    except Exception as e:
        print(f"fetch error ({url}): {e}")
    return None

async def collect_product_links(category_url, limit=LINK_LIMIT):
    async with ClientSession(headers={'User-Agent':'local-bench/1.0'}) as sess:
        html = await fetch(sess, category_url)
        if not html:
            print("Не удалось получить главную страницу")
            return []
        soup = BeautifulSoup(html, 'lxml')
        links = []
        for a in soup.find_all('a', href=True):
            href = urljoin(BASE, a['href'])
            if '/catalog/' in href and href not in links:
                links.append(href)
                if len(links) >= limit:
                    break
        print(f"Собрано {len(links)} ссылок для парсинга")
        return links

async def handle_parse(request):
    start = time.perf_counter()
    links = await collect_product_links(BASE)
    if not links:
        return web.json_response({'error': 'Не удалось собрать ссылки'})

    titles, total_sum = [], 0.0
    seen = set()
    sem = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)

    async with ClientSession(headers={'User-Agent':'local-bench/1.0'}, connector=TCPConnector(limit=MAX_PARALLEL_REQUESTS)) as sess:

        async def fetch_with_sem(url):
            async with sem:
                return await fetch(sess, url)

        htmls = await asyncio.gather(*[fetch_with_sem(link) for link in links])

        for html in htmls:
            if html:
                items, page_sum = parse_content(html)
                for t, price in items:
                    line = f"{t} | {price}"
                    if line not in seen:
                        titles.append([t, price])
                        total_sum += price
                        seen.add(line)

    # Запись в файл
    async with aiofiles.open(RESULT_FILE, 'w', encoding='utf-8') as f:
        for t, price in titles:
            await f.write(f"{t} | {price}\n")

    p = psutil.Process(os.getpid())
    mem = p.memory_info().rss

    print(f"Парсинг завершён: {len(titles)} товаров")
    return web.json_response({
        'server': 'Async',
        'time_ms': (time.perf_counter() - start) * 1000,
        'mem_bytes': mem,
        'count': len(titles),
        'sum': total_sum
    })

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.get('/parse', handle_parse)])
    web.run_app(app, port=9000)
