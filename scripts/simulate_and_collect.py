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

# Limiti del container (AGGIORNA QUESTI per CPU potenti!)
CPU_LIMIT_CORES = 2.0  # Aumentato da 0.5 a 2.0 core
MEMORY_LIMIT_BYTES = 512 * 1024 * 1024  # Aumentato da 256MB a 512MB

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

def get_cpu_usage_percentage():
    """CPU usage percentage"""
    cpu_queries = [
        'sum(rate(container_cpu_usage_seconds_total{container="prime-service"}[30s]))',
        'sum(rate(container_cpu_usage_seconds_total{pod=~"prime-service-.*"}[30s]))',
    ]
    cpu_cores = query_prom_multiple(cpu_queries)
    cpu_percentage = (cpu_cores / CPU_LIMIT_CORES) * 100
    return min(cpu_percentage, 100.0)

def get_memory_usage_percentage():
    """Memory usage percentage"""
    mem_queries = [
        'avg(container_memory_working_set_bytes{container="prime-service"})',
        'avg(container_memory_working_set_bytes{pod=~"prime-service-.*"})',
    ]
    mem_bytes = query_prom_multiple(mem_queries)
    mem_percentage = (mem_bytes / MEMORY_LIMIT_BYTES) * 100
    return min(mem_percentage, 100.0)

def get_replica_count():
    """Ottieni il numero di repliche dal deployment"""
    try:
        cmd = "kubectl get deployment prime-service -n prime-service -o json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            deployment_info = json.loads(result.stdout)
            spec_replicas = deployment_info.get('spec', {}).get('replicas', 1)
            return spec_replicas
        else:
            return 1
    except Exception as e:
        return 1

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
                r = requests.get(PRIME_API.format(n), timeout=15)
                r.raise_for_status()
            except:
                continue
            elapsed = time.time() - start
            with lock:
                response_times.append(elapsed)
        except IndexError:
            break

def scale_deployment(replicas):
    """Scala il deployment a un numero specifico di repliche"""
    try:
        cmd = f"kubectl scale deployment prime-service --replicas={replicas} -n prime-service"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ Scaled to {replicas} replicas")
            return True
        else:
            print(f"  ❌ Scaling failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Scaling error: {e}")
        return False

def wait_for_ready_replicas(target_replicas, max_wait=45):
    """Aspetta che le repliche siano pronte"""
    print(f"  ⏳ Waiting for {target_replicas} replicas...")
    start_wait = time.time()
    
    while time.time() - start_wait < max_wait:
        try:
            cmd = "kubectl get deployment prime-service -n prime-service -o json"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                deployment_info = json.loads(result.stdout)
                available_replicas = deployment_info.get('status', {}).get('availableReplicas', 0)
                
                if available_replicas >= target_replicas:
                    print(f"  ✅ {available_replicas} replicas ready!")
                    time.sleep(8)  # Attesa per stabilizzazione metriche
                    return True
                else:
                    print(f"    Current: {available_replicas}/{target_replicas}")
                    time.sleep(5)
        except Exception as e:
            time.sleep(3)
    
    print(f"  ⚠️ Timeout - proceeding anyway")
    return True

def generate_intensive_load(intensity_level):
    """
    Genera carico MOLTO più intenso e graduale
    intensity_level: 1-50 (50 livelli graduali)
    """
    
    # PARAMETRI ULTRA-AGGRESSIVI per simulare molti più utenti
    base_concurrency = 100        # Partenza più alta
    max_concurrency = 1500       # Fino a 1000 utenti simultanei! 🔥
    
    base_queue_size = 500
    max_queue_size = 7500             # Molto più carico
    
    # Scala lineare dell'intensità
    concurrency = int(base_concurrency + (max_concurrency - base_concurrency) * (intensity_level / 50.0))
    queue_size = int(base_queue_size + (max_queue_size - base_queue_size) * (intensity_level / 50.0))
    
    # Mix di numeri per stressare CPU con diversa difficoltà computazionale
    queue = []
    for _ in range(queue_size):
        difficulty_roll = random.random()
        
        if intensity_level <= 10:
            # Livelli bassi: numeri moderati per iniziare il ramp-up
            if difficulty_roll < 0.5:
                queue.append(random.randint(10000, 100000))      # Medium-fast
            elif difficulty_roll < 0.7:
                queue.append(random.randint(100000, 500000))     # Medium
            else:
                queue.append(random.randint(500000, 1000000))    # Slow
        
        elif intensity_level <= 25:
            # Livelli medi: numeri più impegnativi
            if difficulty_roll < 0.2:
                queue.append(random.randint(100000, 500000))     # Medium
            elif difficulty_roll < 0.5:
                queue.append(random.randint(1000000, 3000000))   # Slow
            else:
                queue.append(random.randint(3000000, 8000000))   # Very slow
        
        else:
            # Livelli alti: numeri ESTREMAMENTE difficili per saturare Ryzen
            if difficulty_roll < 0.1:
                queue.append(random.randint(3000000, 8000000))   # Very slow
            elif difficulty_roll < 0.4:
                queue.append(random.randint(8000000, 25000000))  # ULTRA slow
            else:
                queue.append(random.randint(25000000, 100000000)) # BEAST MODE per Ryzen! 🔥
    
    print(f"    🔥 Generated load: concurrency={concurrency}, queue_size={queue_size}")
    return concurrency, queue

def run_intensive_gradual_simulation():
    """Simulazione intensiva e graduale per dataset ricco"""
    
    print("🚀 INTENSIVE GRADUAL Load Simulation")
    print("=" * 50)
    print("💪 High-stress testing for rich dataset generation")
    print("📈 50 intensity levels × multiple replicas × iterations")
    
    # CONFIGURAZIONI INTENSIVE per dataset ricco
    replica_configs = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]  # 10 configurazioni
    
    # 75 LIVELLI GRADUALI di intensità per granularità fine
    intensity_levels = list(range(1, 76))  # 1, 2, 3, ..., 75
    
    iterations = 3  # Più iterazioni per variabilità statistica
    
    # Inizializza CSV
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "iteration", "replicas", "intensity_level", "concurrent_users",
            "req_per_sec", "response_time_avg", 
            "cpu_percent", "memory_percent", 
            "power_per_container", "total_power"
        ])
    
    total_tests = len(replica_configs) * len(intensity_levels) * iterations
    print(f"🎯 Total tests planned: {total_tests:,}")
    print(f"📊 Expected rich dataset with CPU stress patterns")
    
    test_count = 0
    
    for iteration in range(iterations):
        print(f"\n🔄 ITERATION {iteration+1}/{iterations}")
        
        for replica_count in replica_configs:
            print(f"\n🎯 Testing {replica_count} replicas...")
            
            # Scale deployment
            if scale_deployment(replica_count):
                wait_for_ready_replicas(replica_count)
            
            for intensity_level in intensity_levels:
                test_count += 1
                progress = (test_count / total_tests) * 100
                
                print(f"  🧪 Test {test_count:4d} [{progress:5.1f}%]: level={intensity_level:2d}/50")
                
                # Genera carico INTENSO
                concurrency, queue = generate_intensive_load(intensity_level)
                
                start_time = time.time()
                response_times = []
                
                # Esegui carico con più thread per stress reale
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
                else:
                    actual_rps = 0
                    avg_response_time = 0
                
                # Attesa per lettura metriche accurate
                time.sleep(3)
                
                # Metriche risorse (dovrebbero essere molto più variabili ora!)
                cpu_percent = get_cpu_usage_percentage()
                mem_percent = get_memory_usage_percentage()
                current_replicas = get_replica_count()
                
                # Memoria per calcolo potenza
                mem_bytes = query_prom_multiple([
                    'sum(container_memory_working_set_bytes{container="prime-service"})'
                ]) or (MEMORY_LIMIT_BYTES * mem_percent / 100)
                
                power_per_container = estimate_power_consumption(cpu_percent, mem_bytes, actual_rps)
                total_power = power_per_container * current_replicas
                
                # Salva nel CSV con intensity_level per analisi
                with open(CSV_FILE, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        time.time(), iteration+1, current_replicas, intensity_level, concurrency,
                        round(actual_rps, 1), round(avg_response_time, 4),
                        round(cpu_percent, 1), round(mem_percent, 1),
                        round(power_per_container, 2), round(total_power, 2)
                    ])
                
                # Log con indicatori di stress
                stress_indicator = "🔥" if cpu_percent > 50 else "🔸" if cpu_percent > 20 else "🔹"
                print(f"      {stress_indicator} RPS={actual_rps:.1f}, CPU={cpu_percent:.1f}%, RT={avg_response_time*1000:.0f}ms")
                
                # Pausa ridotta per test più fluidi
                time.sleep(1)
            
            print(f"  ✅ Completed all {len(intensity_levels)} intensity levels for {replica_count} replicas")
            time.sleep(3)  # Pausa tra replica configs
        
        print(f"✅ Iteration {iteration+1} completed")
    
    print(f"\n🎉 INTENSIVE simulation completed!")
    print(f"📄 Total rows generated: {test_count:,}")
    print(f"💾 Saved to: {CSV_FILE}")
    print(f"📈 Dataset should now show rich CPU/memory variation patterns!")

if __name__ == "__main__":
    run_intensive_gradual_simulation()