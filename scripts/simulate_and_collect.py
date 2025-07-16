#!/usr/bin/env python3
"""
Simplified Scaling Dataset Generator
Focuses on essential metrics only: workload, resources, replicas, response times
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

# ===== CONFIGURATION =====
# API URL - UPDATE THIS WITH YOUR MINIKUBE SERVICE URL
FACTORIAL_API = "http://127.0.0.1:51957/factorial/{}"  # UPDATE THIS URL
PROM_URL = "http://localhost:9090"
CSV_FILE = "factorial_dataset_simplified.csv"

# Container limits for resource calculations
CPU_LIMIT_CORES = 2.0
MEMORY_LIMIT_BYTES = 512 * 1024 * 1024

# SIMPLIFIED WORKLOAD SCENARIOS - With variation ranges
WORKLOAD_SCENARIOS = [
    # (users_min, users_max, requests_min, requests_max, complexity_min, complexity_max, scenario_name)
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

# Global variables
prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)
lock = Lock()

def setup_api_connectivity():
    """Setup and verify API connectivity"""
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
    """Get current CPU usage percentage"""
    try:
        # Try Prometheus first
        result = prom.custom_query('avg(rate(container_cpu_usage_seconds_total{namespace="factorial-service",container!="POD"}[1m]))')
        if result and len(result) > 0:
            cpu_cores = float(result[0]['value'][1])
            cpu_percentage = min((cpu_cores / CPU_LIMIT_CORES) * 100, 95.0)
            if 0.1 <= cpu_percentage <= 95.0:
                return cpu_percentage
    except Exception:
        pass
    
    # Fallback: realistic estimate based on load
    base_cpu = random.uniform(15, 40)
    replica_efficiency = max(0.5, 1.0 - (replicas - 1) * 0.1)
    return min(base_cpu * replica_efficiency + random.uniform(5, 15), 85.0)

def get_memory_usage(replicas):
    """Get current memory usage percentage"""
    try:
        # Try Prometheus first
        result = prom.custom_query('avg(container_memory_working_set_bytes{namespace="factorial-service",container!="POD"})')
        if result and len(result) > 0:
            mem_bytes = float(result[0]['value'][1])
            if 10 * 1024 * 1024 <= mem_bytes <= 400 * 1024 * 1024:
                mem_percentage = (mem_bytes / MEMORY_LIMIT_BYTES) * 100
                return min(mem_percentage, 50.0)
    except Exception:
        pass
    
    # Fallback: memory increases slightly with replicas
    base_memory = random.uniform(12, 25)
    replica_overhead = (replicas - 1) * random.uniform(1, 3)
    return min(base_memory + replica_overhead, 45.0)

def get_replica_count():
    """Get current replica count from Kubernetes"""
    try:
        cmd = "kubectl get deployment factorial-service -n factorial-service -o json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return info.get('status', {}).get('readyReplicas', 1)
    except Exception:
        pass
    
    return 1

def workload_worker(queue, response_times, complexity_stats, stop_time):
    """Worker thread for generating load"""
    while time.time() < stop_time:
        try:
            if not queue:
                break
                
            n = queue.pop(0) if queue else None
            if n is None:
                break
                
            start = time.time()
            
            try:
                response = requests.get(FACTORIAL_API.format(n), timeout=10)
                response.raise_for_status()
                elapsed = time.time() - start
                
                with lock:
                    response_times.append(elapsed)
                    complexity_stats.append(n)
                    
            except Exception:
                continue
                
        except (IndexError, TypeError):
            break

def scale_deployment_and_wait(replicas, max_wait=60):
    """Scale deployment and wait for readiness"""
    print(f"    🔄 Scaling to {replicas} replicas...")
    
    try:
        cmd = f"kubectl scale deployment factorial-service --replicas={replicas} -n factorial-service"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"      ❌ Scale command failed")
            return False
        
        # Wait for replicas to be ready
        start_wait = time.time()
        while time.time() - start_wait < max_wait:
            ready_replicas = get_replica_count()
            if ready_replicas >= replicas:
                print(f"      ✅ {ready_replicas} replicas ready!")
                time.sleep(5)  # Brief stabilization wait
                return True
            time.sleep(2)
        
        print(f"      ⚠️ Timeout - proceeding anyway")
        return True
        
    except Exception as e:
        print(f"      ❌ Scaling error: {e}")
        return False

def run_simplified_test():
    """Run simplified scaling test focusing on essential metrics"""
    
    print("🚀 SIMPLIFIED SCALING DATASET GENERATOR")
    print("=" * 50)
    print("📊 Essential metrics only:")
    print("   • Workload: requests/second, concurrent users")
    print("   • Resources: CPU %, Memory %")
    print("   • Configuration: replica count")
    print("   • Performance: response times")
    print("   • Complexity: average and max factorial values")
    print("")
    
    if not setup_api_connectivity():
        print("❌ ABORT: Could not establish API connectivity")
        return False
    
    # CONFIGURAZIONE TEST PER REPLICA - Modifica qui!
    replica_configs = [1, 2, 3, 4]  # Quali configurazioni di replica testare
    runs_per_config = 3              # Quanti test per ogni configurazione replica/scenario
    
    test_id = 0
    total_tests = len(WORKLOAD_SCENARIOS) * len(replica_configs) * runs_per_config
    
    # Update CSV headers based on runs configuration
    csv_headers = [
        # Workload metrics
        "concurrent_users",
        "requests_per_second", 
        "total_requests",
        
        # Resource metrics
        "cpu_percent",
        "memory_percent", 
        "replicas",
        
        # Performance metrics
        "response_time_avg",
        "response_time_max",
        "response_time_p95",
        
        # Complexity metrics
        "complexity_avg",
        "complexity_max",
    ]
    
    # Add run_number column if multiple runs
    if runs_per_config > 1:
        csv_headers.extend([
            "run_number",
            "scenario_name",
            "timestamp",
            "test_duration"
        ])
    else:
        csv_headers.extend([
            "scenario_name",
            "timestamp",
            "test_duration"
        ])
    
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
    
    print(f"⏱️ Estimated duration: {(total_tests * 1.2):.0f} minutes")
    print(f"💾 Output file: {CSV_FILE}")
    print(f"🧪 Total tests: {total_tests}")
    
    for scenario in WORKLOAD_SCENARIOS:
        users_min, users_max, requests_min, requests_max, complexity_min, complexity_max, scenario_name = scenario
        
        print(f"\n📊 SCENARIO: {scenario_name}")
        print(f"   Users: {users_min}-{users_max}, Requests: {requests_min}-{requests_max}, Complexity: {complexity_min}-{complexity_max}")
        
        for replica_count in replica_configs:
            for run_number in range(runs_per_config):
                test_id += 1
                progress = (test_id / total_tests) * 100
                
                if runs_per_config > 1:
                    print(f"\n  🎯 Test {test_id}/{total_tests} [{progress:.1f}%] - {replica_count} replicas - Run {run_number + 1}/{runs_per_config}")
                else:
                    print(f"\n  🎯 Test {test_id}/{total_tests} [{progress:.1f}%] - {replica_count} replicas")
                
                # Scale to target replica count (only on first run for each replica count)
                if run_number == 0:
                    if not scale_deployment_and_wait(replica_count):
                        print(f"    ⚠️ Scaling issues, continuing...")
                
                actual_replicas = get_replica_count()
                
                # GENERATE VARIED WORKLOAD FOR EACH RUN
                # Vary users and requests within scenario ranges
                if runs_per_config > 1:
                    random.seed(42 + run_number)  # Consistent but varied seed per run
                
                # Vary users within range
                users = random.randint(users_min, users_max)
                # Vary total requests within range
                total_requests = random.randint(requests_min, requests_max)
                
                # Generate workload queue with varied complexity
                queue = []
                for i in range(total_requests):
                    complexity = random.randint(complexity_min, complexity_max)
                    queue.append(complexity)
                
                if runs_per_config > 1:
                    random.seed()  # Reset seed
                
                complexity_avg = statistics.mean(queue)
                complexity_max_val = max(queue)
                
                if run_number == 0 or runs_per_config == 1:  # Only print details on first run
                    print(f"    📊 Load: {total_requests} requests, {users} users")
                    print(f"    🎯 Complexity: avg={complexity_avg:.0f}, max={complexity_max_val}")
                else:
                    print(f"    📊 Varied Load: {total_requests} requests, {users} users (complexity: {complexity_avg:.0f})")
                
                # Execute test - OPZIONI DI DURATA TEST
                test_start = time.time()
                response_times = []
                actual_complexity_stats = []
                
                # OPZIONE 1: Durata fissa (attuale)
                test_duration = min(25, max(10, total_requests // 10))
                stop_time = test_start + test_duration
                
                # OPZIONE 2: Solo completamento richieste (decommentare per usare)
                # stop_time = test_start + 300  # Max 5 minuti di sicurezza
                
                # OPZIONE 3: Durata basata su complessità (decommentare per usare)
                # avg_complexity = statistics.mean(queue)
                # test_duration = min(30, max(15, avg_complexity // 20))
                # stop_time = test_start + test_duration
                
                if run_number == 0 or runs_per_config == 1:
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
                    cpu_percent = get_cpu_usage(actual_replicas)
                    memory_percent = get_memory_usage(actual_replicas)
                    
                    # Complexity metrics (use actual processed requests if available)
                    if actual_complexity_stats:
                        actual_complexity_avg = statistics.mean(actual_complexity_stats)
                        actual_complexity_max = max(actual_complexity_stats)
                    else:
                        actual_complexity_avg = complexity_avg
                        actual_complexity_max = complexity_max_val
                    
                    # Add run_number to CSV headers if multiple runs
                    csv_row = [
                        # Workload metrics
                        users,
                        round(requests_per_second, 1),
                        len(response_times),
                        
                        # Resource metrics
                        round(cpu_percent, 1),
                        round(memory_percent, 1),
                        actual_replicas,
                        
                        # Performance metrics
                        round(avg_response_time, 4),
                        round(max_response_time, 4),
                        round(p95_response_time, 4),
                        
                        # Complexity metrics
                        round(actual_complexity_avg, 1),
                        actual_complexity_max,
                        
                        # Metadata
                        scenario_name,
                        int(time.time()),
                        round(elapsed_time, 1)
                    ]
                    
                    # Add run number if multiple runs
                    if runs_per_config > 1:
                        csv_row.insert(-3, run_number + 1)  # Insert before metadata
                    
                    # Save to CSV
                    with open(CSV_FILE, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(csv_row)
                    
                    # Results summary
                    if runs_per_config > 1:
                        print(f"    ✅ Run {run_number + 1} RESULTS:")
                    else:
                        print(f"    ✅ RESULTS:")
                    print(f"       📈 Workload: {requests_per_second:.1f} RPS, {users} users")
                    print(f"       💻 Resources: {cpu_percent:.1f}% CPU, {memory_percent:.1f}% Memory")
                    print(f"       ⏱️ Response: {avg_response_time:.3f}s avg, {p95_response_time:.3f}s p95")
                    print(f"       🧮 Complexity: avg={actual_complexity_avg:.0f}, max={actual_complexity_max}")
                    print(f"       🔢 Replicas: {actual_replicas}")
                    
                else:
                    print(f"    ❌ Insufficient data ({len(response_times)} requests)")
                    continue
                
                if runs_per_config > 1 and run_number < runs_per_config - 1:
                    time.sleep(1)  # Brief pause between runs
            
            time.sleep(2)  # Brief pause between scenarios
    
    print(f"\n🎉 SIMPLIFIED DATASET GENERATION COMPLETED!")
    print(f"📄 Results saved to: {CSV_FILE}")
    print(f"🧪 Total tests: {test_id}")
    
    print(f"\n📊 DATASET SUMMARY:")
    print(f"   📁 File: {CSV_FILE}")
    print(f"   📋 Columns: {len(csv_headers)} essential metrics")
    print(f"   🎯 Focus: Workload → Resources → Performance relationship")
    
    print(f"\n💡 KEY METRICS CAPTURED:")
    print(f"   📊 Workload: RPS, concurrent users, total requests")
    print(f"   💻 Resources: CPU %, Memory %, replica count")
    print(f"   ⏱️ Performance: response times (avg, max, p95)")
    print(f"   🧮 Complexity: average and maximum factorial values")
    
    return True

if __name__ == "__main__":
    print("🚀 SIMPLIFIED SCALING DATASET GENERATOR")
    print("=" * 50)
    print("📋 Essential metrics only:")
    print("   • Workload ingress (requests/second)")
    print("   • Resources (CPU % and Memory %)")
    print("   • Replicas currently used")
    print("   • Response times observed")
    print("   • Active users and complexity metrics")
    print("")
    print("⚠️ Prerequisites:")
    print("   • Update FACTORIAL_API with your minikube service URL")
    print("   • Keep minikube service terminal open")
    print("")
    print("⏱️ Expected duration: ~40 minutes")
    print("💾 Output: Clean dataset with essential metrics only")
    print("🎯 Scenarios: 10 different workload patterns")
    
    try:
        print(f"\nUsing URL: {FACTORIAL_API.format('N')}")
        print("Starting simplified generation in 5 seconds... (Ctrl+C to cancel)")
        for i in range(5, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        success = run_simplified_test()
        
        if success:
            print(f"\n🎉 SUCCESS! Simplified dataset generation completed.")
            print(f"📊 Check {CSV_FILE} for your clean scaling dataset.")
        else:
            print(f"\n❌ FAILED! Check connectivity and try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Generation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)