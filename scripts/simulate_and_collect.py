import time
import csv
import json
from threading import Thread, Lock
import requests
from prometheus_api_client import PrometheusConnect
import statistics
import random
import subprocess

# CONFIGURAZIONE
PRIME_API = "http://localhost:8080/prime/{}"
PROM_URL = "http://localhost:9090"
CSV_FILE = "resource_dataset.csv"

# Limiti del container
CPU_LIMIT_CORES = 0.5
MEMORY_LIMIT_BYTES = 256 * 1024 * 1024

prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)
lock = Lock()

def query_prom_multiple(queries):
    """Prova multiple query fino a trovarne una che funziona"""
    for query in queries:
        try:
            result = prom.custom_query(query=query)
            if result and len(result) > 0:
                return float(result[0]['value'][1])
        except Exception as e:
            continue
    return 0.0

def debug_available_metrics():
    """Debug metriche disponibili"""
    print("\n=== DEBUG: Metriche disponibili ===")
    
    common_metrics = [
        'up', 'prime_requests_total', 'container_cpu_usage_seconds_total',
        'container_memory_working_set_bytes', 'kube_deployment_status_replicas'
    ]
    
    for metric in common_metrics:
        try:
            result = prom.custom_query(query=metric)
            if result:
                print(f"✓ {metric}: {len(result)} serie(s) disponibili")
            else:
                print(f"✗ {metric}: Non disponibile")
        except Exception as e:
            print(f"✗ {metric}: Errore - {e}")

def get_cpu_usage_percentage():
    """CPU usage percentage"""
    cpu_queries = [
        'sum(rate(container_cpu_usage_seconds_total{container="prime-service"}[30s]))',
        'sum(rate(container_cpu_usage_seconds_total{pod=~"prime-service-.*"}[30s]))',
        'sum(rate(process_cpu_seconds_total[30s]))',
    ]
    cpu_cores = query_prom_multiple(cpu_queries)
    cpu_percentage = (cpu_cores / CPU_LIMIT_CORES) * 100
    return min(cpu_percentage, 100.0)

def get_memory_usage_percentage():
    mem_queries = [
        'avg(container_memory_working_set_bytes{container="prime-service"})',  # AVG invece di SUM
        'avg(container_memory_working_set_bytes{pod=~"prime-service-.*"})',
    ]
    mem_bytes = query_prom_multiple(mem_queries)
    mem_percentage = (mem_bytes / MEMORY_LIMIT_BYTES) * 100
    return min(mem_percentage, 100.0)

def get_replica_count():
    """Current replica count"""
    replica_queries = [
        'kube_deployment_status_replicas{deployment="prime-service", namespace="prime-service"}',
        'count(up{job="prime-service"})',
    ]
    result = query_prom_multiple(replica_queries)
    return result if result > 0 else 1

def estimate_power_consumption(cpu_percentage, memory_bytes, requests_per_second):
    """Power consumption estimation"""
    base_power_watts = 1.0
    cpu_max_power_watts = 4.0
    cpu_power_watts = cpu_max_power_watts * ((cpu_percentage / 100.0) ** 1.6)
    
    memory_gb = memory_bytes / (1024**3)
    memory_power_watts = memory_gb * 0.4
    
    io_power_watts = (requests_per_second / 100.0) * 0.1
    infrastructure_overhead = 1.4
    
    direct_power = base_power_watts + cpu_power_watts + memory_power_watts + io_power_watts
    total_power_watts = direct_power * infrastructure_overhead
    
    return total_power_watts

def worker(queue, response_times):
    """Worker per generare carico"""
    while queue:
        try:
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
        except IndexError:
            break

def scale_deployment(replicas):
    """Scala il deployment (versione migliorata)"""
    try:
        cmd = f"kubectl scale deployment prime-service --replicas={replicas} -n prime-service"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Scaling command sent for {replicas} replicas")
            # Tempo di attesa ridotto poiché abbiamo la funzione wait
            time.sleep(5)
            return True
        else:
            print(f"✗ Scaling failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Scaling error: {e}")
        return False

def wait_for_ready_replicas(target_replicas, max_wait=60):
    """Aspetta repliche pronte (corretto)"""
    print(f"Waiting for {target_replicas} replicas...")
    start_wait = time.time()
    
    while time.time() - start_wait < max_wait:
        try:
            cmd = "kubectl get deployment prime-service -n prime-service -o json"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                deployment_info = json.loads(result.stdout)
                
                # CORREZIONE PRINCIPALE: usiamo 'availableReplicas' invece di 'readyReplicas'
                available_replicas = deployment_info.get('status', {}).get('availableReplicas', 0)
                ready_replicas = deployment_info.get('status', {}).get('readyReplicas', 0)
                
                # Preferiamo availableReplicas ma usiamo readyReplicas come fallback
                current_replicas = available_replicas if available_replicas > 0 else ready_replicas
                
                if current_replicas >= target_replicas:
                    print(f"✓ {current_replicas} replicas ready!")
                    return True
                else:
                    print(f"  Current: {current_replicas}, Waiting... {target_replicas}")
                    time.sleep(5)
            else:
                print(f"  kubectl error, retrying...")
                time.sleep(3)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(3)
    
    print(f"✗ Timeout after {max_wait}s - proceeding anyway")
    return True

def generate_varied_load(intensity_base, variation_range=0.3):
    """Genera carico variabile intorno a un'intensità base"""
    # Variazione casuale dell'intensità
    variation = random.uniform(-variation_range, variation_range)
    intensity = max(0.05, min(intensity_base + variation, 2.0))
    
    # Parametri del carico
    concurrency = max(3, int(intensity * 25))
    queue_size = max(20, int(intensity * 80))
    
    # Mix di numeri per variare difficoltà computazionale
    queue = []
    for _ in range(queue_size):
        if random.random() < 0.3:
            # 30% numeri piccoli (veloci)
            queue.append(random.randint(10, 1000))
        elif random.random() < 0.7:
            # 40% numeri medi
            queue.append(random.randint(10**3, 10**5))
        else:
            # 30% numeri grandi (lenti)
            queue.append(random.randint(10**5, 10**6))
    
    return concurrency, queue

def run_resource_focused_simulation():
    """Simulazione focalizzata su risorse per dataset AI"""
    
    debug_available_metrics()
    
    # CONFIGURAZIONI REPLICA IN ORDINE CRESCENTE
    replica_configs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15]
    
    # INTENSITÀ DEL CARICO IN ORDINE CRESCENTE
    load_intensities = [
        0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
        1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0
    ]
    
    # MULTIPLE ITERAZIONI per variabilità
    iterations = 5
    
    # Inizializza CSV - FOCUS SU RISORSE
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "iteration", "actual_req_per_sec", 
            "response_time_avg_s", "response_time_p95_s", "cpu_usage_percent", 
            "memory_usage_percent", "replica_count", "power_per_container_watts", 
            "total_power_watts"
        ])
    
    total_expected_rows = len(replica_configs) * len(load_intensities) * iterations
    print(f"🎯 Target dataset size: {total_expected_rows:,} rows")
    print("📊 Focus: Resource usage patterns for AI scaling decisions")
    print("🔄 Sequential testing: Replicas ↑ | Load intensities ↑")
    
    row_count = 0
    
    for iteration in range(iterations):
        print(f"\n🔄 ITERATION {iteration+1}/{iterations}")
        
        # BREVE RITARDO INIZIALE PER STABILIZZAZIONE
        time.sleep(10)
        
        # PER OGNI REPLICA IN ORDINE CRESCENTE
        for replica_count in replica_configs:
            print(f"\n🎯 Testing {replica_count} replicas...")
            
            # Scale deployment
            if not scale_deployment(replica_count):
                continue
            wait_for_ready_replicas(replica_count)
            
            # PER OGNI INTENSITÀ IN ORDINE CRESCENTE
            for target_intensity in load_intensities:
                row_count += 1
                progress = (row_count / total_expected_rows) * 100
                
                # Genera carico variabile (mantiene la variabilità interna)
                concurrency, queue = generate_varied_load(target_intensity)
                
                start_time = time.time()
                response_times = []
                
                # Esegui carico
                threads = [Thread(target=worker, args=(queue, response_times)) for _ in range(concurrency)]
                for th in threads:
                    th.start()
                for th in threads:
                    th.join()
                
                elapsed = time.time() - start_time
                
                # Calcola metriche performance
                if response_times:
                    actual_rps = len(response_times) / elapsed
                    avg_response_time = statistics.mean(response_times)
                    p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 10 else avg_response_time
                else:
                    actual_rps = 0
                    avg_response_time = 0
                    p95_response_time = 0
                
                # Raccogli metriche risorse
                cpu_percent = get_cpu_usage_percentage()
                mem_percent = get_memory_usage_percentage()
                current_replicas = get_replica_count()
                
                # Memoria in bytes per calcolo energia
                mem_bytes = query_prom_multiple([
                    'sum(container_memory_working_set_bytes{container="prime-service"})'
                ]) or (MEMORY_LIMIT_BYTES * mem_percent / 100)
                
                power_per_container = estimate_power_consumption(cpu_percent, mem_bytes, actual_rps)
                total_power = power_per_container * current_replicas
                
                # Salva nel CSV
                with open(CSV_FILE, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        time.time(), iteration+1, 
                        round(actual_rps, 1), round(avg_response_time, 4), round(p95_response_time, 4),
                        round(cpu_percent, 1), round(mem_percent, 1), int(current_replicas),
                        round(power_per_container, 2), round(total_power, 2)
                    ])
                
                # Log progress
                print(f"  🔄 Intensity: {target_intensity:.1f} | RPS={actual_rps:.1f} | CPU={cpu_percent:.1f}%")
                time.sleep(1)  # Breve pausa tra un'intensità e l'altra
            
            # Fine ciclo intensità - reset per prossima replica
            print(f"✅ Finished all intensities for {replica_count} replicas")
            time.sleep(5)  # Pausa più lunga prima di cambiare replica
    
    print(f"\n🎉 Resource-focused simulation completed!")
    print(f"📄 Total rows: {row_count:,}")
    print(f"🧠 Dataset optimized for AI scaling decisions!")
    """Simulazione focalizzata su risorse per dataset AI"""
    
    debug_available_metrics()
    
    # CONFIGURAZIONI REPLICA ESTESE
    replica_configs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15]
    
    # RANGE DI INTENSITÀ DEL CARICO (focus su risorse)
    load_intensities = [
        0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
        1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0
    ]
    
    # MULTIPLE ITERAZIONI per variabilità
    iterations = 5
    
    # Inizializza CSV - FOCUS SU RISORSE
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "iteration", "actual_req_per_sec", 
            "response_time_avg_s", "response_time_p95_s", "cpu_usage_percent", 
            "memory_usage_percent", "replica_count", "power_per_container_watts", 
            "total_power_watts"
        ])
    
    total_expected_rows = len(replica_configs) * len(load_intensities) * iterations
    print(f"🎯 Target dataset size: {total_expected_rows:,} rows")
    print("📊 Focus: Resource usage patterns for AI scaling decisions")
    
    row_count = 0
    
    for iteration in range(iterations):
        print(f"\n🔄 ITERATION {iteration+1}/{iterations}")
        
        # Randomizza ordine per evitare bias sequenziali
        configs = replica_configs.copy()
        
        for replica_count in configs:
            print(f"\n🎯 Testing {replica_count} replicas...")
            
            # Scale deployment
            if not scale_deployment(replica_count):
                continue
            wait_for_ready_replicas(replica_count)
            
            # Randomizza ordine intensità
            shuffled_loads = load_intensities.copy()
            random.shuffle(shuffled_loads)
            
            for target_intensity in shuffled_loads:
                row_count += 1
                progress = (row_count / total_expected_rows) * 100
                
                # Genera carico variabile
                concurrency, queue = generate_varied_load(target_intensity)
                
                start_time = time.time()
                response_times = []
                
                # Esegui carico
                threads = [Thread(target=worker, args=(queue, response_times)) for _ in range(concurrency)]
                for th in threads:
                    th.start()
                for th in threads:
                    th.join()
                
                elapsed = time.time() - start_time
                
                # Calcola metriche performance
                if response_times:
                    actual_rps = len(response_times) / elapsed
                    avg_response_time = statistics.mean(response_times)
                    p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 10 else avg_response_time
                else:
                    actual_rps = 0
                    avg_response_time = 0
                    p95_response_time = 0
                
                # Raccogli metriche risorse
                cpu_percent = get_cpu_usage_percentage()
                mem_percent = get_memory_usage_percentage()
                current_replicas = get_replica_count()
                
                # Memoria in bytes per calcolo energia
                mem_bytes = query_prom_multiple([
                    'sum(container_memory_working_set_bytes{container="prime-service"})'
                ]) or (MEMORY_LIMIT_BYTES * mem_percent / 100)
                
                power_per_container = estimate_power_consumption(cpu_percent, mem_bytes, actual_rps)
                total_power = power_per_container * current_replicas
                
                # Salva nel CSV
                with open(CSV_FILE, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        time.time(), iteration+1, 
                        round(actual_rps, 1), round(avg_response_time, 4), round(p95_response_time, 4),
                        round(cpu_percent, 1), round(mem_percent, 1), int(current_replicas),
                        round(power_per_container, 2), round(total_power, 2)
                    ])
                
                # Log progress
                if row_count % 50 == 0:
                    print(f"  📊 [{progress:5.1f}%] Row {row_count:,} | RPS={actual_rps:.1f} | RT={avg_response_time*1000:.0f}ms | CPU={cpu_percent:.1f}% | Replicas={current_replicas}")
                
                # Pausa breve per stabilizzazione
                time.sleep(2)
    
    print(f"\n🎉 Resource-focused simulation completed!")
    print(f"📄 Total rows: {row_count:,}")
    print(f"🧠 Dataset optimized for AI scaling decisions!")
    print(f"📊 Features: load → resources → performance → scaling decision")

if __name__ == "__main__":
    run_resource_focused_simulation()