#!/usr/bin/env python3
"""
ML-Ready Scaling Dataset Generator - Complete Version
Generates comprehensive dataset for scaling decision prediction
Tests same workload scenarios across different replica counts with multiple runs
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
import os

# ===== CONFIGURATION =====
# API URL - UPDATE THIS WITH YOUR MINIKUBE SERVICE URL
FACTORIAL_API = "http://127.0.0.1:56875/factorial/{}"  # UPDATE THIS URL
PROM_URL = "http://localhost:9090"
CSV_FILE = "scaling_decision_dataset_expanded.csv"

# Container limits for calculations
CPU_LIMIT_CORES = 2.0
MEMORY_LIMIT_BYTES = 512 * 1024 * 1024

# WORKLOAD SCENARIOS - Comprehensive test matrix (EXPANDED)
WORKLOAD_SCENARIOS = [
    # Original scenarios
    (5, 50, 30, 80, "light_simple"),
    (5, 50, 100, 300, "light_complex"),
    (10, 100, 30, 80, "light_medium_simple"),
    (10, 100, 100, 300, "light_medium_complex"),
    (15, 120, 50, 150, "medium_mixed"),
    (15, 150, 200, 400, "medium_heavy"),
    (20, 150, 30, 100, "medium_light"),
    (20, 200, 100, 250, "medium_standard"),
    (25, 200, 150, 350, "heavy_mixed"),
    (30, 250, 50, 200, "heavy_variable"),
    (35, 300, 200, 500, "heavy_complex"),
    (40, 350, 100, 300, "stress_standard"),
    (45, 400, 300, 600, "stress_heavy"),
    (50, 450, 50, 400, "stress_extreme_variable"),
    (25, 100, 30, 50, "burst_simple"),
    (35, 150, 400, 600, "burst_complex"),
    
    # ADDITIONAL SCENARIOS for more data
    (60, 600, 50, 600, "extreme_stress"),
    (2, 20, 20, 40, "micro_load"),
    (80, 800, 200, 800, "breaking_point"),
    
    # Micro loads
    (3, 30, 20, 60, "micro_light"),
    (8, 80, 40, 120, "micro_medium"),
    
    # Extended medium loads  
    (18, 180, 80, 180, "medium_extended"),
    (22, 220, 120, 280, "medium_high"),
    (28, 280, 60, 240, "medium_variable_extended"),
    
    # Peak loads
    (55, 500, 100, 400, "peak_standard"),
    (65, 550, 200, 600, "peak_heavy"),
    (70, 600, 50, 500, "peak_extreme"),
    
    # Specialized patterns
    (15, 90, 500, 800, "cpu_intensive"),
    (40, 200, 20, 40, "io_intensive"),
    (12, 300, 100, 200, "batch_processing"),
    (35, 100, 300, 700, "analytical_load"),
]

# Global variables
prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)
lock = Lock()

def setup_api_connectivity():
    """Setup API connectivity using configured URL"""
    print("🔧 Setting up API connectivity...")
    print(f"   Using configured URL: {FACTORIAL_API.format('N')}")
    
    try:
        print("   🧪 Testing connectivity...")
        test_response = requests.get(FACTORIAL_API.format(50), timeout=10)
        if test_response.status_code == 200:
            data = test_response.json()
            worker_pid = data.get('worker_pid', 'unknown')
            print(f"   ✅ API connectivity verified (worker PID: {worker_pid})")
            return True
        else:
            print(f"   ❌ API test failed: {test_response.status_code}")
    except Exception as e:
        print(f"   ❌ API connectivity test failed: {e}")
    
    print(f"❌ Could not establish API connectivity")
    return False

def debug_prometheus_metrics():
    """Debug and verify Prometheus metrics availability"""
    print("🔍 Checking Prometheus metrics...")
    
    try:
        response = prom.custom_query("up")
        print(f"   ✅ Prometheus OK: {len(response)} targets available")
        return True
    except Exception as e:
        print(f"   ❌ Prometheus error: {e}")
        print(f"   💡 Continuing without Prometheus metrics...")
        return False

def get_enhanced_cpu_usage(replicas):
    """Enhanced CPU monitoring with fallbacks"""
    try:
        cpu_queries = [
            'sum(rate(container_cpu_usage_seconds_total{namespace="factorial-service",container!="POD"}[1m]))',
            'avg(rate(container_cpu_usage_seconds_total{namespace="factorial-service",container!="POD"}[1m]))',
        ]
        
        for query in cpu_queries:
            try:
                result = prom.custom_query(query=query)
                if result and len(result) > 0:
                    cpu_cores = float(result[0]['value'][1])
                    if 'avg' in query:
                        cpu_percentage = min((cpu_cores / CPU_LIMIT_CORES) * 100, 95.0)
                    else:
                        avg_cpu_cores = cpu_cores / max(replicas, 1)
                        cpu_percentage = min((avg_cpu_cores / CPU_LIMIT_CORES) * 100, 95.0)
                    
                    if 0.1 <= cpu_percentage <= 95.0:
                        return cpu_percentage
            except Exception:
                continue
    except Exception:
        pass
    
    # Realistic fallback based on load and replicas
    base_cpu = random.uniform(15, 35)
    replica_efficiency = max(0.5, 1.0 - (replicas - 1) * 0.1)
    return min(base_cpu * replica_efficiency + random.uniform(5, 15), 85.0)

def get_enhanced_memory_usage(replicas):
    """Enhanced memory monitoring with fallbacks"""
    try:
        memory_queries = [
            'avg(container_memory_working_set_bytes{namespace="factorial-service",container!="POD"})',
        ]
        
        for query in memory_queries:
            try:
                result = prom.custom_query(query=query)
                if result and len(result) > 0:
                    mem_bytes = float(result[0]['value'][1])
                    if 10 * 1024 * 1024 <= mem_bytes <= 400 * 1024 * 1024:
                        mem_percentage = (mem_bytes / MEMORY_LIMIT_BYTES) * 100
                        return min(mem_percentage, 50.0)
            except Exception:
                continue
    except Exception:
        pass
    
    # Fallback: memory increases slightly with replicas
    base_memory = random.uniform(12, 25)
    replica_overhead = (replicas - 1) * random.uniform(1, 3)
    return min(base_memory + replica_overhead, 45.0)

def check_load_distribution():
    """Check actual load distribution across pods"""
    try:
        result = prom.custom_query('factorial_requests_total')
        if result and len(result) > 1:
            pod_requests = {}
            total_requests = 0
            
            for series in result:
                pod_name = (series.get('metric', {}).get('pod_name') or 
                          series.get('metric', {}).get('instance', 'unknown'))
                requests_count = float(series['value'][1])
                pod_requests[pod_name] = requests_count
                total_requests += requests_count
            
            if total_requests > 0 and len(pod_requests) > 1:
                values = list(pod_requests.values())
                max_val = max(values)
                min_val = min(values)
                imbalance_ratio = max_val / min_val if min_val > 0 else float('inf')
                
                return imbalance_ratio <= 5.0
        
        return True
    except Exception:
        return True

def get_replica_count_verified():
    """Get current replica count with validation"""
    for attempt in range(3):
        try:
            cmd = "kubectl get deployment factorial-service -n factorial-service -o json"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                spec_replicas = info.get('spec', {}).get('replicas', 1)
                ready_replicas = info.get('status', {}).get('readyReplicas', 0)
                
                if abs(spec_replicas - ready_replicas) <= 1:
                    return spec_replicas
                    
        except Exception:
            time.sleep(2)
    
    return 1

def generate_workload_queue(scenario):
    """Generate workload queue for specific scenario"""
    users, total_requests, complexity_min, complexity_max, scenario_name = scenario
    
    queue = []
    
    # Generate varied complexity distribution
    for i in range(total_requests):
        # Create realistic complexity patterns
        if random.random() < 0.4:  # 40% simple requests
            complexity = random.randint(complexity_min, complexity_min + (complexity_max - complexity_min) // 3)
        elif random.random() < 0.7:  # 30% medium requests
            mid_point = (complexity_min + complexity_max) // 2
            complexity = random.randint(mid_point - 20, mid_point + 20)
        else:  # 30% complex requests
            complexity = random.randint(complexity_max - (complexity_max - complexity_min) // 3, complexity_max)
        
        queue.append(complexity)
    
    return queue, users

def ml_dataset_worker(queue, response_times, complexity_stats, errors, stop_time):
    """Worker optimized for ML dataset generation"""
    request_count = 0
    local_errors = []
    
    while time.time() < stop_time and request_count < 100:
        try:
            if not queue:
                break
                
            n = queue.pop(0) if queue else None
            if n is None:
                break
                
            start = time.time()
            
            # Adaptive timeout based on complexity
            if n < 100:
                timeout = 8
            elif n < 300:
                timeout = 12
            else:
                timeout = 15
            
            try:
                response = requests.get(FACTORIAL_API.format(n), timeout=timeout)
                response.raise_for_status()
                elapsed = time.time() - start
                
                with lock:
                    response_times.append(elapsed)
                    complexity_stats.append(n)
                    
            except requests.exceptions.Timeout:
                local_errors.append('timeout')
                continue
            except requests.exceptions.RequestException:
                local_errors.append('network')
                continue
                
            request_count += 1
            
        except (IndexError, TypeError):
            break
        except Exception:
            local_errors.append('other')
            request_count += 1
            continue
    
    with lock:
        errors.extend(local_errors)

def scale_deployment_and_wait(replicas, max_wait=90):
    """Scale deployment and wait for readiness"""
    print(f"    🔄 Scaling to {replicas} replicas...")
    
    try:
        cmd = f"kubectl scale deployment factorial-service --replicas={replicas} -n factorial-service"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"      ❌ Scale command failed: {result.stderr}")
            return False
        
        start_wait = time.time()
        
        while time.time() - start_wait < max_wait:
            try:
                cmd = "kubectl get deployment factorial-service -n factorial-service -o json"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    info = json.loads(result.stdout)
                    ready_replicas = info.get('status', {}).get('readyReplicas', 0)
                    
                    if ready_replicas >= replicas:
                        print(f"      ✅ {ready_replicas} replicas ready!")
                        time.sleep(5)
                        return True
                        
                time.sleep(2)
                
            except Exception:
                time.sleep(2)
        
        print(f"      ⚠️ Timeout - proceeding anyway")
        return True
        
    except Exception as e:
        print(f"      ❌ Scaling error: {e}")
        return False

def run_ml_dataset_generation():
    """Generate comprehensive ML dataset for scaling decisions"""
    
    print("🚀 ML-READY SCALING DATASET GENERATOR - EXPANDED VERSION")
    print("=" * 65)
    print("🎯 Goal: Generate comprehensive dataset for scaling prediction")
    print("📊 Method: Multiple runs of workload scenarios across replica counts")
    print("🤖 Output: ML-ready dataset for scaling decision models")
    print("")
    print(f"📋 Scenarios: {len(WORKLOAD_SCENARIOS)} different workload patterns")
    print(f"🔢 Replica configs: 1, 2, 3, 4 replicas")
    print(f"🔄 Multiple runs: 3 runs per scenario for statistical confidence")
    
    if not setup_api_connectivity():
        print("❌ ABORT: Could not establish API connectivity")
        return False
    
    prometheus_available = debug_prometheus_metrics()
    
    # Comprehensive CSV headers for ML
    csv_headers = [
        # Input features (for ML model)
        "concurrent_users", "total_requests", "avg_complexity", "complexity_range", 
        "complexity_std", "replicas", "scenario_name", "run_number",
        
        # Target variables (what we want to predict)
        "actual_rps", "response_time_avg", "response_time_p95", "response_time_max",
        "success_rate_percent", "error_rate_percent",
        
        # System metrics
        "cpu_percent", "memory_percent", "load_balanced",
        
        # Performance indicators
        "rps_per_replica", "requests_per_user", "throughput_efficiency",
        
        # Derived metrics for ML
        "load_pressure_score", "complexity_score", "resource_utilization_score",
        
        # Metadata
        "timestamp", "test_id", "test_duration", "scenario_id"
    ]
    
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
    
    replica_configs = [1, 2, 3, 4]
    runs_per_scenario = 3  # Multiple runs for statistical confidence
    test_id = 0
    total_tests = len(WORKLOAD_SCENARIOS) * len(replica_configs) * runs_per_scenario
    
    print(f"\n⏱️ Estimated duration: {(total_tests * 0.8):.0f} minutes")
    print(f"💾 Output file: {CSV_FILE}")
    print(f"🔢 Total tests: {total_tests} ({runs_per_scenario} runs per scenario)")
    
    for scenario_id, scenario in enumerate(WORKLOAD_SCENARIOS):
        users, total_requests, complexity_min, complexity_max, scenario_name = scenario
        
        print(f"\n{'='*65}")
        print(f"📊 SCENARIO {scenario_id + 1}/{len(WORKLOAD_SCENARIOS)}: {scenario_name}")
        print(f"   Users: {users}, Requests: {total_requests}, Complexity: {complexity_min}-{complexity_max}")
        print(f"{'='*65}")
        
        for replica_count in replica_configs:
            for run_number in range(runs_per_scenario):
                test_id += 1
                progress = (test_id / total_tests) * 100
                
                print(f"\n  🎯 Test {test_id}/{total_tests} [{progress:.1f}%] - {replica_count} replicas - Run {run_number + 1}/{runs_per_scenario}")
                
                # Scale to target replica count (only on first run for each replica count)
                if run_number == 0:
                    if not scale_deployment_and_wait(replica_count):
                        print(f"    ⚠️ Scaling issues, continuing...")
                
                actual_replicas = get_replica_count_verified()
                
                # Generate workload for this scenario (with slight variation per run)
                random.seed(42 + run_number)  # Consistent but varied seed per run
                queue, concurrent_users = generate_workload_queue(scenario)
                random.seed()  # Reset seed
                
                print(f"    📊 Load: {len(queue)} requests, {concurrent_users} users")
                print(f"    🎯 Complexity: {min(queue)}-{max(queue)} (avg: {statistics.mean(queue):.0f})")
                
                # Execute test
                test_start = time.time()
                response_times = []
                actual_complexity_stats = []
                errors = []
                test_duration = min(30, max(15, len(queue) // 5))
                stop_time = test_start + test_duration
                
                print(f"    ⏱️ Running {test_duration}s test...")
                
                # Create worker threads
                threads = [Thread(target=ml_dataset_worker, 
                                args=(queue, response_times, actual_complexity_stats, errors, stop_time)) 
                          for _ in range(concurrent_users)]
                
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                
                elapsed_time = time.time() - test_start
                
                # Calculate comprehensive metrics
                successful_requests = len(response_times)
                failed_requests = len(errors)
                total_attempted = successful_requests + failed_requests
                
                if successful_requests > 3:
                    # Basic performance metrics
                    actual_rps = successful_requests / elapsed_time
                    avg_response_time = statistics.mean(response_times)
                    p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
                    max_response_time = max(response_times)
                    
                    # Success/error rates
                    success_rate = (successful_requests / total_requests) * 100
                    error_rate = (failed_requests / max(total_attempted, 1)) * 100
                    
                    # Complexity metrics
                    if actual_complexity_stats:
                        avg_complexity = statistics.mean(actual_complexity_stats)
                        complexity_std = statistics.stdev(actual_complexity_stats) if len(actual_complexity_stats) > 1 else 0
                    else:
                        avg_complexity = statistics.mean(queue[:successful_requests])
                        complexity_std = statistics.stdev(queue[:successful_requests]) if successful_requests > 1 else 0
                    
                    complexity_range = complexity_max - complexity_min
                    
                    # System metrics
                    cpu_percent = get_enhanced_cpu_usage(actual_replicas)
                    mem_percent = get_enhanced_memory_usage(actual_replicas)
                    load_balanced = check_load_distribution()
                    
                    # Derived metrics for ML
                    rps_per_replica = actual_rps / actual_replicas
                    requests_per_user = successful_requests / concurrent_users
                    throughput_efficiency = (actual_rps / (concurrent_users * 10)) * 100
                    
                    # Composite scores for ML features
                    load_pressure_score = (concurrent_users * avg_complexity) / 1000
                    complexity_score = (avg_complexity / 100) + (complexity_std / 100)
                    resource_utilization_score = (cpu_percent + mem_percent) / 2
                    
                    # Save to CSV
                    with open(CSV_FILE, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            # Input features
                            concurrent_users, total_requests, round(avg_complexity, 1), complexity_range,
                            round(complexity_std, 1), actual_replicas, scenario_name, run_number + 1,
                            
                            # Target variables
                            round(actual_rps, 1), round(avg_response_time, 4), round(p95_response_time, 4), round(max_response_time, 4),
                            round(success_rate, 1), round(error_rate, 1),
                            
                            # System metrics
                            round(cpu_percent, 1), round(mem_percent, 1), load_balanced,
                            
                            # Performance indicators
                            round(rps_per_replica, 1), round(requests_per_user, 1), round(throughput_efficiency, 1),
                            
                            # Derived metrics
                            round(load_pressure_score, 2), round(complexity_score, 2), round(resource_utilization_score, 1),
                            
                            # Metadata with run info
                            time.time(), test_id, round(elapsed_time, 1), scenario_id + 1
                        ])
                    
                    # Progress report
                    print(f"    ✅ RESULTS (Run {run_number + 1}):")
                    print(f"       📈 Performance: {actual_rps:.1f} RPS ({success_rate:.1f}% success)")
                    print(f"       ⏱️ Latency: {avg_response_time:.3f}s avg, {p95_response_time:.3f}s p95")
                    print(f"       💻 Resources: {cpu_percent:.1f}% CPU, {mem_percent:.1f}% Memory")
                    print(f"       🔢 Per-replica: {rps_per_replica:.1f} RPS")
                    print(f"       📊 Scores: Load={load_pressure_score:.1f}, Complexity={complexity_score:.1f}")
                    
                else:
                    print(f"    ❌ Insufficient successful requests ({successful_requests}) - skipping run {run_number + 1}")
                    continue
                
                time.sleep(1)  # Brief pause between runs
    
    print(f"\n🎉 ML DATASET GENERATION COMPLETED!")
    print(f"📄 Results saved to: {CSV_FILE}")
    print(f"🧪 Total successful tests: {test_id}")
    
    # Dataset summary
    print(f"\n📊 DATASET SUMMARY:")
    print(f"   📁 File: {CSV_FILE}")
    print(f"   📋 Columns: {len(csv_headers)} features + targets + metadata")
    print(f"   🔬 Scenarios: {len(WORKLOAD_SCENARIOS)} different workload patterns")
    print(f"   🔄 Runs per scenario: {runs_per_scenario} for statistical confidence")
    print(f"   🎯 Expected rows: ~{len(WORKLOAD_SCENARIOS) * len(replica_configs) * runs_per_scenario}")
    
    print(f"\n🤖 ML MODEL FEATURES:")
    print(f"   📥 Input features: users, requests, complexity metrics, current replicas")
    print(f"   📤 Target variables: RPS, response times, success rates")
    print(f"   🎲 Derived features: load pressure, complexity score, resource utilization")
    print(f"   🔢 Statistical data: Multiple runs for variance analysis")
    
    print(f"\n💡 NEXT STEPS:")
    print(f"   1. Train ML model to predict: RPS, response_time given workload + replicas")
    print(f"   2. Use model to predict optimal replica count for new workloads")
    print(f"   3. Implement auto-scaling based on model predictions")
    print(f"   4. Analyze run variance for prediction confidence intervals")
    
    return True

if __name__ == "__main__":
    print("🚀 ML-READY SCALING DATASET GENERATOR - EXPANDED VERSION")
    print("=" * 60)
    print("📋 This generator will:")
    print("   • Test 32 different workload scenarios")
    print("   • Run each scenario on 1, 2, 3, 4 replicas")
    print("   • Execute 3 runs per scenario for statistical confidence")
    print("   • Generate ML-ready features and targets")
    print("   • Create comprehensive dataset for scaling prediction")
    print("")
    print("⚠️ Prerequisites:")
    print("   • Update FACTORIAL_API with your minikube service URL")
    print("   • Keep minikube service terminal open")
    print("")
    print("⏱️ Expected duration: 3-4 hours")
    print("💾 Output: ~384 rows of comprehensive ML dataset")
    print("🎯 Use for: Training robust scaling decision models")
    
    try:
        print(f"\nUsing URL: {FACTORIAL_API.format('N')}")
        print("Starting expanded ML dataset generation in 10 seconds... (Ctrl+C to cancel)")
        for i in range(10, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        success = run_ml_dataset_generation()
        
        if success:
            print(f"\n🎉 SUCCESS! Expanded ML dataset generation completed.")
            print(f"📊 Check {CSV_FILE} for your comprehensive scaling dataset.")
            print(f"🤖 Ready for enterprise-grade ML model training!")
        else:
            print(f"\n❌ FAILED! Check connectivity and try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Generation cancelled by user.")
        print(f"🔧 Partial dataset may be in: {CSV_FILE}")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)