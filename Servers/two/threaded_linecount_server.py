from flask import Flask, jsonify
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import time
import random
import string

DIRECTORY = 'data_files'
NUM_FILES = 50
MIN_LINES = 100
MAX_LINES = 1000
MAX_WORKERS = 10


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

app = Flask(__name__)

def count_lines_in_file(file_path):
    count = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for _ in f:
                count += 1
    except:
        pass
    return count

@app.route('/count', methods=['GET'])
def handle_count():
    start = time.perf_counter()
    files = [os.path.join(DIRECTORY, f) for f in os.listdir(DIRECTORY) if os.path.isfile(os.path.join(DIRECTORY, f))]
    total_lines = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(count_lines_in_file, f) for f in files]
        for future in as_completed(futures):
            total_lines += future.result()

    mem = psutil.Process().memory_info().rss
    duration = time.perf_counter() - start

    return jsonify({
        'total_lines': total_lines,
        'time_s': duration,
        'mem_bytes': mem
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8085, threaded=True)
