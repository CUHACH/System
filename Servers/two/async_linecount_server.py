import asyncio
from aiohttp import web, TCPConnector
import aiofiles
import os
import time
import psutil
import random
import string


DIRECTORY = 'data_files'
NUM_FILES = 50
MIN_LINES = 100
MAX_LINES = 1000
MAX_PARALLEL_REQUESTS = 20


os.makedirs(DIRECTORY, exist_ok=True)
for f in os.listdir(DIRECTORY):
    path = os.path.join(DIRECTORY, f)
    if os.path.isfile(path):
        os.remove(path)

for i in range(1, NUM_FILES + 1):
    filename = os.path.join(DIRECTORY, f'file_{i}.txt')
    num_lines = random.randint(MIN_LINES, MAX_LINES)
    with open(filename, 'w', encoding='utf-8') as f:
        for _ in range(num_lines):
            line = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            f.write(line + '\n')




async def count_lines_in_file(file_path):
    count = 0
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            async for _ in f:
                count += 1
    except:
        pass
    return count

async def handle_count(request):
    start = time.perf_counter()
    files = [os.path.join(DIRECTORY, f) for f in os.listdir(DIRECTORY) if os.path.isfile(os.path.join(DIRECTORY, f))]
    sem = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)

    async def count_with_sem(file_path):
        async with sem:
            return await count_lines_in_file(file_path)

    results = await asyncio.gather(*[count_with_sem(f) for f in files])
    total_lines = sum(results)

    mem = psutil.Process(os.getpid()).memory_info().rss
    duration = time.perf_counter() - start

    return web.json_response({
        'total_lines': total_lines,
        'time_s': duration,
        'mem_bytes': mem
    })

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.get('/count', handle_count)])
    web.run_app(app, port=9000)
