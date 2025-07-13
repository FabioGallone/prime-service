import time
import csv
from threading import Thread, Lock
import requests
from prometheus_api_client import PrometheusConnect
import statistics
import random

# CONFIGURAZIONE
PRIME_API = "http://localhost:8080/prime/{}"
PROM_URL = "http://localhost:9090"
SCRAPE_INTERVAL = 5
DURATION = 300
CONCURRENCY = 10
CSV_FILE = "prime_dataset.csv"

prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)
lock = Lock()

def worker(queue, response_times):
    while queue:
        n = queue.pop()
        start = time.time()
        try:
            r = requests.get(PRIME_API.format(n), timeout=10)
            r.raise_for_status()
        except:
            continue
        elapsed = time.time() - start
        with lock:
            response_times.append(elapsed)

def query_prom(query):
    try:
        result = prom.custom_query(query=query)
        if result and len(result) > 0:
            return float(result[0]['value'][1])
        return 0.0
    except Exception as e:
        print(f"Errore query '{query}': {e}")
        return 0.0

def query_prom_multiple(queries):
    """Prova multiple query fino a trovarne una che funziona"""
    for query in queries:
        try:
            result = prom.custom_query(query=query)
            if result and len(result) > 0:
                print(f"Query funzionante: {query}")
                return float(result[0]['value'][1])
        except Exception as e:
            print(f"Query fallita '{query}': {e}")
    return 0.0

# Test delle query disponibili
print("Testing available metrics...")
test_queries = [
    'prime_requests_total',
    'prime_inprogress_requests', 
    'prime_request_latency_seconds_sum',
    'kube_deployment_status_replicas{deployment="prime-service"}',
    'container_cpu_usage_seconds_total',
    'container_memory_working_set_bytes',
    'up'
]

for query in test_queries:
    result = query_prom(query)
    print(f"{query}: {result}")

# Inizializza CSV
with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "req_per_sec", "avg_latency_s", "cpu_usage_cores", "memory_usage_bytes", "replica_count", "energy_joules"])

print("\nInizio simulazione...")
t0 = time.time()
iteration = 0

while time.time() - t0 < DURATION:
    start = time.time()
    queue = [random.randint(10**5, 10**6) for _ in range(CONCURRENCY * 10)]
    response_times = []
    threads = [Thread(target=worker, args=(queue, response_times)) for _ in range(CONCURRENCY)]
    for th in threads: th.start()
    for th in threads: th.join()

    elapsed = time.time() - start
    rps = len(response_times) / elapsed if elapsed else 0
    avg_lat = statistics.mean(response_times) if response_times else 0

    # Query per CPU - prova diverse alternative
    cpu_queries = [
        'sum(rate(container_cpu_usage_seconds_total{namespace="prime-service", container="prime-service"}[30s]))',
        'sum(rate(container_cpu_usage_seconds_total{pod=~"prime-service-.*"}[30s]))'
    ]
    cpu = query_prom_multiple(cpu_queries)

    # Query per memoria - prova diverse alternative
    mem_queries = [
        'sum(container_memory_working_set_bytes{namespace="prime-service", container="prime-service"})',
        'sum(container_memory_working_set_bytes{pod=~"prime-service-.*"})'
    ]
    mem = query_prom_multiple(mem_queries)

    # Query per replica
    replicas_queries = [
        'kube_deployment_status_replicas{deployment="prime-service", namespace="prime-service"}'
    ]
    replicas = query_prom_multiple(replicas_queries)
    if replicas == 0.0:
        replicas = 1  # Fallback

    energy = 0.0  # Non disponibile in cluster normali

    # Log dettagliato ogni 5 iterazioni
    if iteration % 5 == 0:
        print(f"Iteration {iteration}: RPS={rps:.2f}, Latency={avg_lat:.4f}s, CPU={cpu:.3f}, Memory={mem}, Replicas={replicas}")

    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([time.time(), round(rps, 2), round(avg_lat, 4), 
                        round(cpu, 3), int(mem), int(replicas), round(energy, 2)])

    iteration += 1
    time.sleep(max(0, SCRAPE_INTERVAL - (time.time() - start)))

print(f"Dataset salvato in {CSV_FILE}")

# Mostra metriche finali disponibili
print("\nMetriche finali disponibili:")
final_queries = [
    'prime_requests_total',
    'prime_inprogress_requests',
    'sum(prime_requests_total)',
    'sum(rate(prime_requests_total[1m]))',
]

for query in final_queries:
    result = query_prom(query)
    print(f"{query}: {result}")