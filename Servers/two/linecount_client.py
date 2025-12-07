import asyncio
import aiohttp
import time

SERVERS = [
    ('Async', 'http://localhost:9000/count'),
    ('Threaded', 'http://localhost:8085/count')
]

NUM_REQUESTS = 5

async def run_test(name, url, num_requests=NUM_REQUESTS):
    server_time_sum = 0
    client_time_sum = 0
    max_memory = 0

    async def fetch(session, idx):
        nonlocal server_time_sum, client_time_sum, max_memory
        start = time.perf_counter()
        try:
            async with session.get(url, timeout=600) as resp:
                data = await resp.json()
        except Exception as e:
            print(f"{name} запрос {idx+1} ошибка: {e}")
            return
        duration = time.perf_counter() - start

        server_time_sum += data.get('time_s', 0)
        client_time_sum += duration
        max_memory = max(max_memory, data.get('mem_bytes', 0))

    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, i) for i in range(num_requests)]
        await asyncio.gather(*tasks)

    print(f"=== {name} ИТОГ ЗА {num_requests} одновременных запросов ===")
    print(f"Суммарное серверное время: {server_time_sum:.3f}s")
    print(f"Среднее клиентское время: {client_time_sum/num_requests:.3f}s")
    print(f"Пиковая память сервера: {max_memory/1024/1024:.2f} MB\n")

if __name__ == '__main__':
    asyncio.run(run_test(SERVERS[0][0], SERVERS[0][1]))
    asyncio.run(run_test(SERVERS[1][0], SERVERS[1][1]))
