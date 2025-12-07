import subprocess
import time
import requests
import psutil
from threading import Thread

SERVERS = [
    ('threaded_server.py', 'Threaded-Flask', 'http://localhost:8085/parse'),
    ('async_server.py', 'Async', 'http://localhost:9000/parse')
]

def start_server(script, url):
    """Запускает сервер через subprocess и ждёт его готовности."""
    proc = subprocess.Popen(
        ['python', script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    print(f"{script} запущен с PID: {proc.pid} на {url}")
    return proc

def wait_for_server(url, timeout=15):
    """Ждём, пока сервер реально ответит на /parse."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except:
            time.sleep(0.2)
    print(f"Предупреждение: сервер {url} не ответил за {timeout} секунд")
    return False

def run_test(url, name, pid):
    """Выполняет запрос к серверу и выводит результаты по времени и памяти."""
    start = time.perf_counter()
    try:
        r = requests.get(url, timeout=600)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"{name} ошибка:", e)
        return
    duration = time.perf_counter() - start

    p = psutil.Process(pid)
    mem = p.memory_info().rss / 1024 / 1024

    print(f"{name}: {duration:.2f}s, Память: {mem:.2f} MB")


if __name__ == '__main__':
    processes = []

    # 1. Запуск всех серверов
    for script, name, url in SERVERS:
        proc = start_server(script, url)
        processes.append((proc, name, url))

    # 2. Одновременное ожидание готовности серверов
    threads = []
    for _, name, url in processes:
        t = Thread(target=wait_for_server, args=(url,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    # 3. Тестирование серверов
    for proc, name, url in processes:
        run_test(url, name, proc.pid)

    # 4. Остановка серверов
    for proc, _, _ in processes:
        proc.terminate()
        proc.wait()
    print("Серверы остановлены.")
