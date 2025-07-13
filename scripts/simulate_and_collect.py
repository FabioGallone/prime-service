import time
import csv
import json
from threading import Thread, Lock
import requests
from prometheus_api_client import PrometheusConnect
import statistics
import random
import numpy as np
from datetime import datetime, timedelta
import subprocess
import math

# CONFIGURAZIONE
PRIME_API = "http://localhost:8080/prime/{}"
PROM_URL = "http://localhost:9090"
CSV_FILE = "prime_dataset_comprehensive.csv"

# Limiti del container
CPU_LIMIT_CORES = 0.5
MEMORY_LIMIT_BYTES = 256 * 1024 * 1024

prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)
lock = Lock()

class LoadPattern:
    """Definisce i pattern di carico realistici"""
    
    @staticmethod
    def business_hours_pattern(hour_of_day):
        """Simula pattern di carico aziendale (9-17)"""
        if 9 <= hour_of_day <= 17:
            # Picco durante orario lavorativo con variazioni
            base = 0.8
            lunch_dip = 0.6 if 12 <= hour_of_day <= 13 else 1.0
            return base * lunch_dip + random.uniform(-0.2, 0.2)
        elif 18 <= hour_of_day <= 22:
            # Sera - traffico moderato
            return 0.4 + random.uniform(-0.1, 0.1)
        else:
            # Notte - traffico minimo
            return 0.1 + random.uniform(-0.05, 0.05)
    
    @staticmethod
    def ecommerce_pattern(hour_of_day):
        """Simula pattern e-commerce (picchi serali)"""
        if 19 <= hour_of_day <= 22:
            # Picco serale
            return 0.9 + random.uniform(-0.1, 0.1)
        elif 12 <= hour_of_day <= 14:
            # Picco pranzo
            return 0.6 + random.uniform(-0.1, 0.1)
        elif 8 <= hour_of_day <= 18:
            # Giorno normale
            return 0.4 + random.uniform(-0.1, 0.1)
        else:
            # Notte
            return 0.2 + random.uniform(-0.05, 0.05)
    
    @staticmethod
    def social_media_pattern(hour_of_day):
        """Simula pattern social media (picchi mattina/sera)"""
        if hour_of_day in [8, 9, 10] or hour_of_day in [18, 19, 20, 21]:
            # Picchi mattina/sera
            return 0.8 + random.uniform(-0.1, 0.1)
        elif 11 <= hour_of_day <= 17:
            # Giorno
            return 0.5 + random.uniform(-0.1, 0.1)
        else:
            # Notte
            return 0.15 + random.uniform(-0.05, 0.05)
    
    @staticmethod
    def viral_spike_pattern(hour_of_day, spike_probability=0.05):
        """Simula spike virali improvvisi"""
        base_load = LoadPattern.social_media_pattern(hour_of_day)
        if random.random() < spike_probability:
            # Spike virale - aumenta il carico di 3-10x
            spike_multiplier = random.uniform(3, 10)
            return min(base_load * spike_multiplier, 2.0)  # Cap a 2.0
        return base_load

class UserBehavior:
    """Simula comportamenti utente realistici"""
    
    @staticmethod
    def generate_realistic_requests(load_intensity, duration_seconds=60):
        """Genera richieste con pattern realistici"""
        # Calcola numero totale di richieste basato sull'intensità
        base_rps = 50  # RPS di base per load_intensity = 1.0
        target_rps = base_rps * load_intensity
        total_requests = int(target_rps * duration_seconds)
        
        # Genera timestamp realistici (non uniformi)
        timestamps = []
        current_time = 0
        
        for _ in range(total_requests):
            # Inter-arrival time segue distribuzione esponenziale (processo di Poisson)
            if target_rps > 0:
                inter_arrival = random.expovariate(target_rps)
                current_time += inter_arrival
                if current_time < duration_seconds:
                    timestamps.append(current_time)
        
        # Genera numeri primi realistici per l'app
        requests = []
        for ts in timestamps:
            # Distribuzione realistica dei numeri richiesti
            if random.random() < 0.4:
                # 40% - numeri piccoli (risposta veloce)
                num = random.randint(2, 1000)
            elif random.random() < 0.8:
                # 40% - numeri medi (risposta normale)
                num = random.randint(1000, 100000)
            else:
                # 20% - numeri grandi (calcolo intensivo)
                num = random.randint(100000, 10000000)
            
            requests.append((ts, num))
        
        return sorted(requests, key=lambda x: x[0])

def worker(request_queue, response_times, start_time):
    """Worker che esegue le richieste con timing realistico"""
    while request_queue:
        try:
            timestamp, number = request_queue.pop(0)
            
            # Aspetta il momento giusto per fare la richiesta
            elapsed = time.time() - start_time
            if timestamp > elapsed:
                time.sleep(timestamp - elapsed)
            
            req_start = time.time()
            try:
                r = requests.get(PRIME_API.format(number), timeout=30)
                r.raise_for_status()
                elapsed_req = time.time() - req_start
                
                with lock:
                    response_times.append(elapsed_req)
            except Exception as e:
                print(f"Request failed: {e}")
                continue
                
        except IndexError:
            break
        except Exception as e:
            print(f"Worker error: {e}")
            break

def scale_deployment(replicas):
    """Scala il deployment a un numero specifico di repliche"""
    try:
        cmd = f"kubectl scale deployment prime-service --replicas={replicas} -n prime-service"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Scaling to {replicas} replicas...")
            # Aspetta che il scaling sia completato
            time.sleep(30)  # Tempo per startup dei pod
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
                if ready_replicas == target_replicas:
                    print(f"✓ All {target_replicas} replicas are ready!")
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

def get_metrics():
    """Raccoglie tutte le metriche necessarie"""
    try:
        # CPU percentage
        cpu_queries = [
            'sum(rate(container_cpu_usage_seconds_total{namespace="prime-service", container="prime-service"}[30s]))',
            'sum(rate(container_cpu_usage_seconds_total{container="prime-service"}[30s]))'
        ]
        cpu_cores = 0
        for query in cpu_queries:
            try:
                result = prom.custom_query(query=query)
                if result and len(result) > 0:
                    cpu_cores = float(result[0]['value'][1])
                    break
            except:
                continue
        
        cpu_percent = min((cpu_cores / CPU_LIMIT_CORES) * 100, 100.0)
        
        # Memory percentage
        mem_queries = [
            'sum(container_memory_working_set_bytes{namespace="prime-service", container="prime-service"})',
            'sum(container_memory_working_set_bytes{container="prime-service"})'
        ]
        mem_bytes = 0
        for query in mem_queries:
            try:
                result = prom.custom_query(query=query)
                if result and len(result) > 0:
                    mem_bytes = float(result[0]['value'][1])
                    break
            except:
                continue
        
        mem_percent = min((mem_bytes / MEMORY_LIMIT_BYTES) * 100, 100.0)
        
        # Replica count
        replica_queries = [
            'kube_deployment_status_replicas{deployment="prime-service", namespace="prime-service"}',
            'kube_deployment_status_replicas{deployment="prime-service"}'
        ]
        replicas = 1
        for query in replica_queries:
            try:
                result = prom.custom_query(query=query)
                if result and len(result) > 0:
                    replicas = int(float(result[0]['value'][1]))
                    break
            except:
                continue
        
        # Power consumption per container
        power_per_container = estimate_power_consumption(cpu_percent, mem_bytes, 0)
        
        return cpu_percent, mem_percent, replicas, power_per_container
        
    except Exception as e:
        print(f"Error getting metrics: {e}")
        return 0, 0, 1, 1.4

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

def run_comprehensive_simulation():
    """Esegue simulazione completa con diversi scenari"""
    
    # Scenari di test
    scenarios = [
        # (nome, pattern_function, replica_configs, duration_per_config)
        ("business_hours", LoadPattern.business_hours_pattern, [1, 2, 3, 5], 180),
        ("ecommerce", LoadPattern.ecommerce_pattern, [1, 2, 4, 6, 8], 180),
        ("social_media", LoadPattern.social_media_pattern, [1, 3, 5, 7, 10], 180),
        ("viral_spike", LoadPattern.viral_spike_pattern, [1, 2, 5, 8, 12, 15], 120),
    ]
    
    # Inizializza CSV
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "scenario", "simulated_hour", "load_intensity", 
            "req_per_sec", "response_time_avg_s",
            "cpu_usage_percent", "memory_usage_percent", "replica_count", 
            "power_per_container_watts", "total_power_watts",
            "queue_length", "error_rate_percent"
        ])
    
    print("🚀 Starting comprehensive load simulation for AI training dataset")
    print(f"📊 Total scenarios: {len(scenarios)}")
    
    for scenario_name, pattern_func, replica_configs, duration in scenarios:
        print(f"\n{'='*60}")
        print(f"📈 SCENARIO: {scenario_name.upper()}")
        print(f"🔄 Replica configurations: {replica_configs}")
        print(f"⏱️  Duration per config: {duration}s")
        
        for replica_count in replica_configs:
            print(f"\n🎯 Testing with {replica_count} replicas...")
            
            # Scale deployment
            if not scale_deployment(replica_count):
                print(f"❌ Failed to scale to {replica_count} replicas, skipping...")
                continue
            
            # Wait for replicas to be ready
            if not wait_for_ready_replicas(replica_count):
                print(f"❌ Replicas not ready, skipping this configuration...")
                continue
            
            # Simula 24 ore in versione accelerata
            hours_to_simulate = 24
            time_compression = duration / (hours_to_simulate * 3600)  # Comprimi 24h in duration secondi
            
            print(f"⚡ Time compression: {time_compression:.4f}x (24h -> {duration}s)")
            
            test_start_time = time.time()
            sample_interval = 10  # Campiona ogni 10 secondi
            
            for sample in range(0, duration, sample_interval):
                sample_start = time.time()
                
                # Calcola l'ora simulata
                simulated_hour = (sample / duration) * 24
                hour_of_day = int(simulated_hour) % 24
                
                # Ottieni intensità del carico per quest'ora
                load_intensity = pattern_func(hour_of_day)
                load_intensity = max(0.05, min(load_intensity, 2.0))  # Clamp tra 0.05 e 2.0
                
                # Genera richieste realistiche
                requests = UserBehavior.generate_realistic_requests(
                    load_intensity, 
                    duration_seconds=sample_interval
                )
                
                if not requests:
                    requests = [(5, 17)]  # Almeno una richiesta di test
                
                # Esegui le richieste
                response_times = []
                error_count = 0
                
                # Usa thread pool limitato basato sulle richieste
                max_workers = min(20, len(requests))
                request_queue = list(requests)
                
                threads = []
                for _ in range(max_workers):
                    t = Thread(target=worker, args=(request_queue, response_times, sample_start))
                    t.start()
                    threads.append(t)
                
                # Aspetta completion con timeout
                for t in threads:
                    t.join(timeout=sample_interval + 5)
                
                # Calcola metriche delle richieste
                if response_times:
                    avg_latency = statistics.mean(response_times)
                    actual_rps = len(response_times) / sample_interval
                else:
                    avg_latency = 0
                    actual_rps = 0
                
                error_rate = (error_count / max(1, len(requests))) * 100
                queue_length = len(request_queue)  # Richieste non processate
                
                # Ottieni metriche sistema
                cpu_percent, mem_percent, current_replicas, power_per_container = get_metrics()
                total_power = power_per_container * current_replicas
                
                # Scrivi nel CSV
                with open(CSV_FILE, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        time.time(), scenario_name, f"{hour_of_day:02d}:00", 
                        round(load_intensity, 3), round(actual_rps, 2), 
                        round(avg_latency, 4),
                        round(cpu_percent, 1), round(mem_percent, 1), current_replicas,
                        round(power_per_container, 2), round(total_power, 2),
                        queue_length, round(error_rate, 1)
                    ])
                
                # Log progress
                elapsed_in_scenario = time.time() - test_start_time
                progress = (elapsed_in_scenario / duration) * 100
                print(f"  [{progress:5.1f}%] Hour {hour_of_day:02d}:00 | Load={load_intensity:.2f} | RPS={actual_rps:.1f} | ResponseTime={avg_latency*1000:.0f}ms | CPU={cpu_percent:.1f}% | Replicas={current_replicas}")
                
                # Mantieni intervallo di campionamento
                elapsed_sample = time.time() - sample_start
                if elapsed_sample < sample_interval:
                    time.sleep(sample_interval - elapsed_sample)
            
            print(f"✅ Completed {replica_count} replicas configuration")
    
    print(f"\n🎉 Comprehensive simulation completed!")
    print(f"📄 Dataset saved to: {CSV_FILE}")
    print(f"🧠 Ready for AI model training!")

if __name__ == "__main__":
    run_comprehensive_simulation()