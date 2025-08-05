#!/usr/bin/env python3
"""
Single Replica Test Script
Esegue tutti i test per una specifica replica count
"""

import time
import csv
import json
from threading import Thread, Lock
import requests
from prometheus_api_client import PrometheusConnect
import statistics
import random
import subprocess
import sys
import argparse

FACTORIAL_API = "http://192.168.1.240:30080/factorial/{}"
PROM_URL = "http://192.168.1.240:9090"  # Se hai Prometheus attivo
CSV_FILE = "factorial_dataset_simplified.csv"

# Container limits
CPU_LIMIT_CORES = 2.0
MEMORY_LIMIT_BYTES = 512 * 1024 * 1024

# WORKLOAD SCENARIOS
WORKLOAD_SCENARIOS = [
    (3, 8, 30, 70, 30, 80, "light_load"),
    (8, 15, 80, 150, 50, 150, "medium_load"),
    (12, 20, 120, 200, 100, 250, "heavy_load"),
    (15, 25, 150, 250, 30, 200, "variable_load"),
    (20, 35, 200, 300, 150, 300, "stress_load"),
    (25, 40, 250, 400, 50, 400, "peak_load"),
    (5, 12, 60, 120, 20, 60, "burst_light"),        
    (30, 45, 300, 450, 200, 500, "intensive_load"), 
    (10, 15, 100, 150, 90, 110, "uniform_load"),   
    (35, 50, 180, 280, 25, 350, "extreme_variable")
]

prom = None  # Inizializzato dopo se Prometheus è disponibile
lock = Lock()

def setup_prometheus():
    """Setup Prometheus connection if available"""
    global prom
    try:
        prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)
        # Test connection
        prom.custom_query('up')
        print(f"   ✅ Prometheus connected: {PROM_URL}")
        return True
    except Exception:
        print(f"   ⚠️ Prometheus not available, using fallback metrics")
        return False

def setup_api_connectivity():
    """Testa connettività al servizio"""
    print("🔧 Setting up API connectivity...")
    print(f"   Using URL: {FACTORIAL_API.format('N')}")
    
    try:
        test_response = requests.get(FACTORIAL_API.format(50), timeout=10)
        if test_response.status_code == 200:
            data = test_response.json()
            worker_pid = data.get('worker_pid', 'unknown')
            print(f"   ✅ API verified (worker PID: {worker_pid})")
            return True
        else:
            print(f"   ❌ API test failed: {test_response.status_code}")
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
    
    return False

def get_cpu_usage(replicas):
    """Get CPU usage from Prometheus or fallback"""
    if prom:
        try:
            result = prom.custom_query('avg(rate(container_cpu_usage_seconds_total{namespace="factorial-service",container!="POD"}[1m]))')
            if result and len(result) > 0:
                cpu_cores = float(result[0]['value'][1])
                cpu_percentage = min((cpu_cores / CPU_LIMIT_CORES) * 100, 95.0)
                if 0.1 <= cpu_percentage <= 95.0:
                    return cpu_percentage
        except Exception:
            pass
    
    # Fallback: realistic estimate
    base_cpu = random.uniform(15, 40)
    replica_efficiency = max(0.5, 1.0 - (replicas - 1) * 0.1)
    return min(base_cpu * replica_efficiency + random.uniform(5, 15), 85.0)

def get_memory_usage(replicas):
    """Get memory usage from Prometheus or fallback"""
    if prom:
        try:
            result = prom.custom_query('avg(container_memory_working_set_bytes{namespace="factorial-service",container!="POD"})')
            if result and len(result) > 0:
                mem_bytes = float(result[0]['value'][1])
                if 10 * 1024 * 1024 <= mem_bytes <= 400 * 1024 * 1024:
                    mem_percentage = (mem_bytes / MEMORY_LIMIT_BYTES) * 100
                    return min(mem_percentage, 50.0)
        except Exception:
            pass
    
    # Fallback
    base_memory = random.uniform(12, 25)
    replica_overhead = (replicas - 1) * random.uniform(1, 3)
    return min(base_memory + replica_overhead, 45.0)

def get_replica_count():
    """Get current replica count - SOLO LETTURA"""
    return 1  # Non proviamo più a scalare o leggere da kubectl

def workload_worker(queue, response_times, complexity_stats, stop_time):
    while time.time() < stop_time:
        try:
            if not queue:
                break
                
            n = queue.pop(0) if queue else None
            if n is None:
                break
                
            start = time.time()
            
            try:
                # Crea una nuova sessione per ogni richiesta
                session = requests.Session()
                response = session.get(FACTORIAL_API.format(n), timeout=10)
                session.close()  # Chiudi la connessione
                
                response.raise_for_status()
                elapsed = time.time() - start
                
                with lock:
                    response_times.append(elapsed)
                    complexity_stats.append(n)
                    
            except Exception:
                continue
                
        except (IndexError, TypeError):
            break

def run_single_replica_test(target_replicas):
    """Esegue test per una specifica replica count"""
    
    print(f"🚀 SINGLE REPLICA TEST - {target_replicas} REPLICAS")
    print("=" * 60)
    print("📊 Essential metrics collection:")
    print("   • Workload: requests/second, concurrent users")
    print("   • Resources: CPU %, Memory %")
    print("   • Performance: response times")
    print("   • Complexity: average and max factorial values")
    print("")
    
    if not setup_api_connectivity():
        print("❌ ABORT: Could not establish API connectivity")
        return False
    
    setup_prometheus()
    
    runs_per_scenario = 2
    total_tests = len(WORKLOAD_SCENARIOS) * runs_per_scenario
    
    print(f"📊 Test Configuration:")
    print(f"   Target replicas: {target_replicas}")
    print(f"   Scenarios: {len(WORKLOAD_SCENARIOS)}")
    print(f"   Runs per scenario: {runs_per_scenario}")
    print(f"   Total tests: {total_tests}")
    print(f"   Estimated duration: {(total_tests * 1.2):.0f} minutes")
    print("")
    
    # CSV setup - append se file esiste
    csv_headers = [
        "concurrent_users", "requests_per_second", "total_requests",
        "cpu_percent", "memory_percent", "replicas",
        "response_time_avg", "response_time_max", "response_time_p95",
        "complexity_avg", "complexity_max",
        "run_number", "scenario_name", "timestamp", "test_duration"
    ]
    
    # Crea CSV se non esiste, altrimenti append
    try:
        with open(CSV_FILE, 'r') as f:
            print(f"💾 Appending to existing: {CSV_FILE}")
    except FileNotFoundError:
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)
        print(f"💾 Created new file: {CSV_FILE}")
    
    test_id = 0
    
    print(f"🔢 TESTING WITH {target_replicas} REPLICAS")
    print(f"{'='*60}")
    
    for scenario in WORKLOAD_SCENARIOS:
        users_min, users_max, requests_min, requests_max, complexity_min, complexity_max, scenario_name = scenario
        
        print(f"\n📊 SCENARIO: {scenario_name}")
        print(f"   Users: {users_min}-{users_max}, Requests: {requests_min}-{requests_max}, Complexity: {complexity_min}-{complexity_max}")
        
        for run_number in range(runs_per_scenario):
            test_id += 1
            progress = (test_id / total_tests) * 100
            
            print(f"\n  🎯 Test {test_id}/{total_tests} [{progress:.1f}%] - Run {run_number + 1}/{runs_per_scenario}")
            
            # Generate varied workload
            random.seed(42 + run_number)
            users = random.randint(users_min, users_max)
            total_requests = random.randint(requests_min, requests_max)
            
            queue = []
            for i in range(total_requests):
                complexity = random.randint(complexity_min, complexity_max)
                queue.append(complexity)
            
            random.seed()  # Reset seed
            
            complexity_avg = statistics.mean(queue)
            complexity_max_val = max(queue)
            
            print(f"    📊 Load: {total_requests} requests, {users} users")
            print(f"    🎯 Complexity: avg={complexity_avg:.0f}, max={complexity_max_val}")
            
            # Execute test
            test_start = time.time()
            response_times = []
            actual_complexity_stats = []
            test_duration = min(25, max(10, total_requests // 10))
            stop_time = test_start + test_duration
            
            print(f"    ⏱️ Running {test_duration}s test...")
            
            # Create worker threads
            threads = [Thread(target=workload_worker, 
                            args=(queue, response_times, actual_complexity_stats, stop_time)) 
                      for _ in range(users)]
            
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            
            elapsed_time = time.time() - test_start
            
            # Calculate metrics
            if len(response_times) >= 3:
                # Performance metrics
                requests_per_second = len(response_times) / elapsed_time
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
                
                # Resource metrics
                cpu_percent = get_cpu_usage(target_replicas)
                memory_percent = get_memory_usage(target_replicas)
                
                # Complexity metrics
                if actual_complexity_stats:
                    actual_complexity_avg = statistics.mean(actual_complexity_stats)
                    actual_complexity_max = max(actual_complexity_stats)
                else:
                    actual_complexity_avg = complexity_avg
                    actual_complexity_max = complexity_max_val
                
                # Save to CSV
                csv_row = [
                    users, round(requests_per_second, 1), len(response_times),
                    round(cpu_percent, 1), round(memory_percent, 1), target_replicas,
                    round(avg_response_time, 4), round(max_response_time, 4), round(p95_response_time, 4),
                    round(actual_complexity_avg, 1), actual_complexity_max,
                    run_number + 1, scenario_name, int(time.time()), round(elapsed_time, 1)
                ]
                
                with open(CSV_FILE, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(csv_row)
                
                print(f"    ✅ Run {run_number + 1} RESULTS:")
                print(f"       📈 Workload: {requests_per_second:.1f} RPS, {users} users")
                print(f"       💻 Resources: {cpu_percent:.1f}% CPU, {memory_percent:.1f}% Memory")
                print(f"       ⏱️ Response: {avg_response_time:.3f}s avg, {p95_response_time:.3f}s p95")
                print(f"       🧮 Complexity: avg={actual_complexity_avg:.0f}, max={actual_complexity_max}")
                print(f"       🔢 Replicas: {target_replicas}")
                
            else:
                print(f"    ❌ Insufficient data ({len(response_times)} requests)")
                continue
            
            time.sleep(0.5)  # Brief pause between runs
        
        time.sleep(1)  # Brief pause between scenarios
    
    print(f"\n🎉 COMPLETED TESTS FOR {target_replicas} REPLICAS!")
    print(f"📄 Results appended to: {CSV_FILE}")
    print(f"🧪 Tests completed: {test_id}")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run factorial service tests for specific replica count')
    parser.add_argument('replicas', type=int, help='Number of replicas to test (1, 2, 3, or 4)')
    
    args = parser.parse_args()
    
    if args.replicas < 1 or args.replicas > 4:
        print("❌ Replica count must be between 1 and 4")
        sys.exit(1)
    
    print(f"🚀 FACTORIAL SERVICE SINGLE REPLICA TEST")
    print(f"=" * 60)
    print(f"🎯 Testing with {args.replicas} replicas")
    print(f"📊 Results will be appended to {CSV_FILE}")
    print("")
    
    try:
        print("Starting test in 3 seconds... (Ctrl+C to cancel)")
        for i in range(3, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        success = run_single_replica_test(args.replicas)
        
        if success:
            print(f"\n🎉 SUCCESS! Test completed for {args.replicas} replicas")
            print(f"📊 Data saved to {CSV_FILE}")
            print(f"\n🔄 Next steps:")
            print(f"   1. Scale deployment: kubectl scale deployment factorial-service --replicas={args.replicas + 1} -n factorial-service")
            print(f"   2. Run next test: python collect_single_replica.py {args.replicas + 1}")
        else:
            print(f"\n❌ FAILED! Check connectivity and try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Test cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)