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
CSV_FILE = "cloud_dataset.csv"

# Limiti del container
CPU_LIMIT_CORES = 0.5
MEMORY_LIMIT_BYTES = 256 * 1024 * 1024

prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)
lock = Lock()

def query_prom_multiple(queries):
    """Prova multiple query fino a trovarne una che funziona (VERSIONE FUNZIONANTE)"""
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
    """Debug per scoprire quali metriche sono disponibili (VERSIONE FUNZIONANTE)"""
    print("\n=== DEBUG: Metriche disponibili ===")
    
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

def get_cpu_usage_percentage():
    """Usa le query FUNZIONANTI del vecchio script"""
    cpu_queries = [
        # Query per container specifici (QUELLE CHE FUNZIONAVANO)
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
    
    cpu_cores = query_prom_multiple(cpu_queries)
    # Converte in percentuale rispetto al limite del container
    cpu_percentage = (cpu_cores / CPU_LIMIT_CORES) * 100
    return min(cpu_percentage, 100.0)  # Cap al 100%

def get_memory_usage_percentage():
    """Usa le query FUNZIONANTI del vecchio script"""
    mem_queries = [
        # Query per container specifici (QUELLE CHE FUNZIONAVANO)
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
    
    mem_bytes = query_prom_multiple(mem_queries)
    # Converte in percentuale rispetto al limite del container
    mem_percentage = (mem_bytes / MEMORY_LIMIT_BYTES) * 100
    return min(mem_percentage, 100.0)  # Cap al 100%

def get_replica_count():
    """Usa le query FUNZIONANTI del vecchio script"""
    replica_queries = [
        'kube_deployment_status_replicas{deployment="prime-service", namespace="prime-service"}',
        'kube_deployment_status_replicas{deployment="prime-service"}',
        'kube_deployment_spec_replicas{deployment="prime-service"}',
        'count(up{job="prime-service"})',
        'count(prime_requests_total)'
    ]
    
    result = query_prom_multiple(replica_queries)
    return result if result > 0 else 1  # Fallback a 1

def estimate_power_consumption(cpu_percentage, memory_bytes, requests_per_second):
    """Stima consumo energetico realistico per container"""
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

class LoadPattern:
    """Pattern di carico realistici"""
    
    @staticmethod
    def business_hours_pattern(hour_of_day):
        """Pattern business (9-17)"""
        if 9 <= hour_of_day <= 17:
            base = 0.8
            lunch_dip = 0.6 if 12 <= hour_of_day <= 13 else 1.0
            return base * lunch_dip + random.uniform(-0.2, 0.2)
        elif 18 <= hour_of_day <= 22:
            return 0.4 + random.uniform(-0.1, 0.1)
        else:
            return 0.1 + random.uniform(-0.05, 0.05)
    
    @staticmethod
    def ecommerce_pattern(hour_of_day):
        """Pattern e-commerce (picchi serali)"""
        if 19 <= hour_of_day <= 22:
            return 0.9 + random.uniform(-0.1, 0.1)
        elif 12 <= hour_of_day <= 14:
            return 0.6 + random.uniform(-0.1, 0.1)
        elif 8 <= hour_of_day <= 18:
            return 0.4 + random.uniform(-0.1, 0.1)
        else:
            return 0.2 + random.uniform(-0.05, 0.05)
    
    @staticmethod
    def social_media_pattern(hour_of_day):
        """Pattern social media (picchi mattina/sera)"""
        if hour_of_day in [8, 9, 10] or hour_of_day in [18, 19, 20, 21]:
            return 0.8 + random.uniform(-0.1, 0.1)
        elif 11 <= hour_of_day <= 17:
            return 0.5 + random.uniform(-0.1, 0.1)
        else:
            return 0.15 + random.uniform(-0.05, 0.05)
    
    @staticmethod
    def viral_spike_pattern(hour_of_day, spike_probability=0.1):
        """Pattern con spike improvvisi"""
        base_load = LoadPattern.social_media_pattern(hour_of_day)
        if random.random() < spike_probability:
            spike_multiplier = random.uniform(2, 5)
            return min(base_load * spike_multiplier, 2.0)
        return base_load

def worker(queue, response_times):
    """Worker semplificato come nel vecchio script"""
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
    """Scala il deployment"""
    try:
        cmd = f"kubectl scale deployment prime-service --replicas={replicas} -n prime-service"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Scaling to {replicas} replicas...")
            time.sleep(30)  # Aspetta startup
            return True
        else:
            print(f"✗ Scaling failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Scaling error: {e}")
        return False

def wait_for_ready_replicas(target_replicas, max_wait=120):
    """Aspetta che tutte le repliche siano pronte"""
    print(f"Waiting for {target_replicas} replicas to be ready...")
    start_wait = time.time()
    
    while time.time() - start_wait < max_wait:
        try:
            cmd = "kubectl get deployment prime-service -n prime-service -o json"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                deployment_info = json.loads(result.stdout)
                ready_replicas = deployment_info.get('status', {}).get('readyReplicas', 0)
                if ready_replicas >= target_replicas:
                    print(f"✓ At least {target_replicas} replicas are ready (found {ready_replicas})!")
                    return True
                else:
                    print(f"  Waiting... {ready_replicas}/{target_replicas} ready")
                    time.sleep(10)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Error checking readiness: {e}")
            time.sleep(5)
    
    print(f"✗ Timeout waiting for replicas to be ready")
    return False

def run_comprehensive_simulation():
    """Simulazione completa con approccio FUNZIONANTE"""
    
    # Esegui debug iniziale (COME NEL VECCHIO SCRIPT)
    debug_available_metrics()
    
    # Scenari completi per training AI
    scenarios = [
        ("business_hours", LoadPattern.business_hours_pattern, [1, 2, 3, 5], 180),
        ("ecommerce", LoadPattern.ecommerce_pattern, [1, 2, 4, 6], 180),
        ("social_media", LoadPattern.social_media_pattern, [1, 3, 5, 8], 180),
        ("viral_spike", LoadPattern.viral_spike_pattern, [1, 2, 5, 10], 120),
    ]
    
    # Inizializza CSV
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "scenario", "simulated_hour", "load_intensity", 
            "req_per_sec", "response_time_avg_s",
            "cpu_usage_percent", "memory_usage_percent", "replica_count", 
            "power_per_container_watts", "total_power_watts"
        ])
    
    print("🚀 Starting comprehensive simulation for AI training dataset")
    print(f"📊 Total scenarios: {len(scenarios)}")
    total_tests = sum(len(replica_configs) * 7 for _, _, replica_configs, _ in scenarios)
    print(f"🎯 Total tests: {total_tests}")
    
    test_count = 0
    
    for scenario_name, pattern_func, replica_configs, duration in scenarios:
        print(f"\n{'='*60}")
        print(f"📈 SCENARIO: {scenario_name.upper()}")
        print(f"🔄 Replica configurations: {replica_configs}")
        
        for replica_count in replica_configs:
            print(f"\n🎯 Testing with {replica_count} replicas...")
            
            # Scale deployment
            if not scale_deployment(replica_count):
                print(f"❌ Failed to scale, skipping...")
                continue
            
            # Wait for replicas to be ready
            if not wait_for_ready_replicas(replica_count):
                print(f"❌ Replicas not ready, skipping...")
                continue
            
            # Test per ore diverse (dataset più ricco)
            for hour in [8, 9, 12, 15, 18, 20, 22]:  # 7 ore di test
                test_count += 1
                progress = (test_count / total_tests) * 100
                print(f"  📊 [{progress:5.1f}%] Testing hour {hour}:00...")
                
                # Ottieni load intensity per quest'ora
                load_intensity = pattern_func(hour)
                load_intensity = max(0.1, min(load_intensity, 1.5))
                
                # Genera carico come nel VECCHIO SCRIPT FUNZIONANTE
                concurrency = max(5, int(load_intensity * 20))
                queue_size = max(50, int(load_intensity * 100))
                
                start = time.time()
                queue = [random.randint(10**5, 10**6) for _ in range(queue_size)]
                response_times = []
                
                threads = [Thread(target=worker, args=(queue, response_times)) for _ in range(concurrency)]
                for th in threads: th.start()
                for th in threads: th.join()
                
                elapsed = time.time() - start
                rps = len(response_times) / elapsed if elapsed else 0
                avg_lat = statistics.mean(response_times) if response_times else 0
                
                # USA LE FUNZIONI FUNZIONANTI
                cpu_percent = get_cpu_usage_percentage()
                mem_percent = get_memory_usage_percentage()
                current_replicas = get_replica_count()
                
                # Ottieni memoria in bytes per calcolo energia
                mem_bytes_raw = query_prom_multiple([
                    'sum(container_memory_working_set_bytes{namespace="prime-service", container="prime-service"})',
                    'sum(container_memory_working_set_bytes{container="prime-service"})'
                ])
                
                power_per_container = estimate_power_consumption(cpu_percent, mem_bytes_raw, rps)
                total_power = power_per_container * current_replicas
                
                # Log come nel vecchio script
                print(f"    Hour {hour}:00 | Load={load_intensity:.2f} | RPS={rps:.1f} | ResponseTime={avg_lat*1000:.0f}ms | CPU={cpu_percent:.1f}% | Memory={mem_percent:.1f}% | Power={power_per_container:.2f}W | Replicas={current_replicas}")
                
                # Scrivi nel CSV
                with open(CSV_FILE, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        time.time(), scenario_name, f"{hour:02d}:00", 
                        round(load_intensity, 3), round(rps, 2), 
                        round(avg_lat, 4),
                        round(cpu_percent, 1), round(mem_percent, 1), int(current_replicas),
                        round(power_per_container, 2), round(total_power, 2)
                    ])
                
                # Pausa tra test per stabilizzare metriche
                time.sleep(5)
            
            print(f"✅ Completed {replica_count} replicas configuration")
    
    print(f"\n🎉 Comprehensive simulation completed!")
    print(f"📄 Dataset saved to: {CSV_FILE}")
    print(f"📊 Total data points collected: {test_count}")
    print(f"🧠 Ready for AI model training!")

if __name__ == "__main__":
    run_comprehensive_simulation()