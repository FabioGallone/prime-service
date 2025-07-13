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
            continue
    return 0.0

def debug_available_metrics():
    """Debug per scoprire quali metriche sono disponibili"""
    print("\n=== DEBUG: Metriche disponibili ===")
    
    # Lista delle metriche più comuni
    common_metrics = [
        'up',
        'prometheus_build_info',
        'prime_requests_total',
        'prime_inprogress_requests',
        'prime_request_latency_seconds_sum',
        'prime_request_latency_seconds_count',
        'container_cpu_usage_seconds_total',
        'container_memory_working_set_bytes',
        'container_memory_usage_bytes',
        'kube_deployment_status_replicas',
        'kube_pod_info',
        'cadvisor_version_info'
    ]
    
    for metric in common_metrics:
        try:
            result = prom.custom_query(query=metric)
            if result:
                print(f"✓ {metric}: {len(result)} serie(s) disponibili")
                # Mostra i primi 3 risultati con i loro label
                for i, r in enumerate(result[:3]):
                    labels = {k: v for k, v in r['metric'].items() if k != '__name__'}
                    print(f"  [{i}] Valore: {r['value'][1]}, Labels: {labels}")
            else:
                print(f"✗ {metric}: Non disponibile")
        except Exception as e:
            print(f"✗ {metric}: Errore - {e}")

def get_cpu_usage():
    """Prova diverse query per ottenere l'utilizzo CPU"""
    cpu_queries = [
        # Query per container specifici
        'sum(rate(container_cpu_usage_seconds_total{namespace="prime-service", container="prime-service"}[30s]))',
        'sum(rate(container_cpu_usage_seconds_total{container="prime-service"}[30s]))',
        'sum(rate(container_cpu_usage_seconds_total{pod=~"prime-service-.*"}[30s]))',
        
        # Query più generiche
        'sum(rate(container_cpu_usage_seconds_total{namespace="prime-service"}[30s]))',
        'sum(rate(container_cpu_usage_seconds_total{container!="POD", container!=""}[30s]))',
        
        # Query alternative
        'sum(rate(process_cpu_seconds_total[30s]))',
        'rate(container_cpu_usage_seconds_total[30s])'
    ]
    
    return query_prom_multiple(cpu_queries)

def get_memory_usage():
    """Prova diverse query per ottenere l'utilizzo memoria"""
    mem_queries = [
        # Query per container specifici
        'sum(container_memory_working_set_bytes{namespace="prime-service", container="prime-service"})',
        'sum(container_memory_working_set_bytes{container="prime-service"})',
        'sum(container_memory_working_set_bytes{pod=~"prime-service-.*"})',
        
        # Query più generiche
        'sum(container_memory_working_set_bytes{namespace="prime-service"})',
        'sum(container_memory_working_set_bytes{container!="POD", container!=""})',
        
        # Query alternative
        'sum(container_memory_usage_bytes{namespace="prime-service", container="prime-service"})',
        'sum(process_resident_memory_bytes)',
        'container_memory_working_set_bytes'
    ]
    
    return query_prom_multiple(mem_queries)

def get_replica_count():
    """Prova diverse query per ottenere il numero di repliche"""
    replica_queries = [
        'kube_deployment_status_replicas{deployment="prime-service", namespace="prime-service"}',
        'kube_deployment_status_replicas{deployment="prime-service"}',
        'kube_deployment_spec_replicas{deployment="prime-service"}',
        'count(up{job="prime-service"})',
        'count(prime_requests_total)'
    ]
    
    result = query_prom_multiple(replica_queries)
    return result if result > 0 else 1  # Fallback a 1

# Esegui debug iniziale
debug_available_metrics()

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

    # Usa le nuove funzioni per ottenere metriche
    cpu = get_cpu_usage()
    mem = get_memory_usage()
    replicas = get_replica_count()
    energy = 0.0  # Non disponibile in cluster normali

    # Log dettagliato ogni 5 iterazioni
    if iteration % 5 == 0:
        print(f"Iteration {iteration}: RPS={rps:.2f}, Latency={avg_lat:.4f}s, CPU={cpu:.3f}, Memory={mem:.0f}, Replicas={replicas}")

    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([time.time(), round(rps, 2), round(avg_lat, 4), 
                        round(cpu, 3), int(mem), int(replicas), round(energy, 2)])

    iteration += 1
    time.sleep(max(0, SCRAPE_INTERVAL - (time.time() - start)))

print(f"Dataset salvato in {CSV_FILE}")

# Mostra metriche finali disponibili
print("\n=== METRICHE FINALI ===")
print(f"CPU Usage: {get_cpu_usage():.3f} cores")
print(f"Memory Usage: {get_memory_usage():.0f} bytes")
print(f"Replica Count: {get_replica_count()}")
print(f"Prime Requests Total: {query_prom('sum(prime_requests_total)')}")
print(f"Prime Requests Rate: {query_prom('sum(rate(prime_requests_total[1m]))')}")