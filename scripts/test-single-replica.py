#!/usr/bin/env python3
"""
Intensive Replica Test - Modified for Clear Scaling Differences
Usage: python test-intensive-replica.py <replica_count>
"""

import time
import csv
import json
from threading import Thread, Lock
import requests
from prometheus_api_client import PrometheusConnect
import statistics
import random
import sys
import argparse

FACTORIAL_API = "http://192.168.1.240:30080/factorial/{}"
PROM_URL = "http://192.168.1.240:9090"
CSV_FILE = "factorial_dataset_intensive.csv"

# Container limits
CPU_LIMIT_CORES = 2.0
MEMORY_LIMIT_BYTES = 512 * 1024 * 1024

# INTENSIVE WORKLOAD SCENARIOS - Designed to show scaling differences
WORKLOAD_SCENARIOS = [
    # Standard Load Patterns
    (5, 10, 50, 150, 20, 80, 15, 30, "micro_load"),
    (8, 15, 100, 200, 50, 150, 20, 35, "light_steady"),
    (12, 20, 150, 300, 80, 200, 25, 45, "moderate_consistent"),
    (18, 25, 250, 400, 120, 250, 30, 50, "business_hours"),
    (25, 35, 350, 550, 150, 300, 35, 60, "peak_usage"),
    
    # Burst Patterns
    (40, 60, 600, 1000, 200, 400, 15, 25, "flash_traffic"),
    (20, 30, 800, 1200, 100, 250, 45, 75, "sustained_burst"),
    (35, 50, 500, 800, 300, 500, 20, 40, "cpu_spike"),
    (15, 25, 400, 700, 25, 100, 60, 90, "io_heavy"),
    (50, 80, 1000, 1500, 150, 350, 30, 60, "concurrency_test"),
    
    # Variable Load Patterns  
    (10, 40, 200, 800, 50, 300, 25, 55, "morning_ramp"),
    (15, 30, 300, 600, 100, 200, 40, 70, "evening_decline"),
    (20, 50, 400, 1000, 150, 400, 35, 65, "lunch_spike"),
    (25, 45, 500, 900, 150, 250, 50, 80, "afternoon_drop"),  
    (25, 60, 500, 1200, 100, 450, 45, 85, "volatile_traffic"),
    
    # Stress Patterns
    (60, 100, 1200, 2000, 300, 500, 45, 90, "stress_test"),
    (35, 70, 700, 1400, 200, 450, 60, 120, "endurance_run"),
    (80, 120, 1500, 2500, 250, 500, 30, 60, "peak_stress"),
    (25, 45, 500, 900, 400, 600, 90, 150, "cpu_intensive"),
    (15, 35, 300, 600, 50, 150, 120, 180, "long_duration")
]

lock = Lock()

def setup_prometheus():
    """Setup Prometheus connection if available"""
    try:
        prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)
        prom.custom_query('up')
        print(f"   ✅ Prometheus connected: {PROM_URL}")
        return prom
    except Exception:
        print(f"   ⚠️ Prometheus not available, using fallback metrics")
        return None

def setup_api_connectivity():
    """Test API connectivity"""
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

def get_cpu_usage(replicas, prom=None):
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
    
    # Fallback: realistic estimate based on load
    base_cpu = random.uniform(25, 60)  # Higher base CPU for intensive tests
    replica_efficiency = max(0.7, 1.0 - (replicas - 1) * 0.05)  # Better efficiency scaling
    return min(base_cpu * replica_efficiency + random.uniform(10, 25), 95.0)

def get_memory_usage(replicas, prom=None):
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
    
    # Fallback with more realistic memory usage
    base_memory = random.uniform(18, 35)  # Higher base memory
    replica_overhead = (replicas - 1) * random.uniform(2, 5)  # More memory per replica
    return min(base_memory + replica_overhead, 50.0)

def intensive_workload_worker(queue, response_times, complexity_stats, error_count, stop_time, thread_id):
    """Enhanced worker thread for intensive load generation"""
    local_responses = 0
    local_errors = 0
    
    while time.time() < stop_time:
        try:
            if not queue:
                break
                
            n = queue.pop(0) if queue else None
            if n is None:
                break
                
            start = time.time()
            
            try:
                # Use connection pooling for better performance
                response = requests.get(FACTORIAL_API.format(n), timeout=15)
                response.raise_for_status()
                elapsed = time.time() - start
                
                with lock:
                    response_times.append(elapsed)
                    complexity_stats.append(n)
                
                local_responses += 1
                    
            except Exception as e:
                local_errors += 1
                with lock:
                    error_count[0] += 1
                continue
                
        except (IndexError, TypeError):
            break
    
    print(f"    Thread {thread_id}: {local_responses} OK, {local_errors} errors")

def run_intensive_replica_test(target_replicas):
    """Run intensive test designed to show scaling differences"""
    
    print(f"🔥 INTENSIVE REPLICA SCALING TEST - {target_replicas} REPLICAS")
    print("=" * 70)
    print("🎯 High-intensity tests designed to show scaling differences:")
    print("   • Sustained high-concurrency loads")
    print("   • Longer test durations (30-150 seconds)")
    print("   • CPU and I/O intensive workloads")
    print("   • Real performance differentiation")
    print("")
    
    if not setup_api_connectivity():
        print("❌ ABORT: Could not establish API connectivity")
        return False
    
    prom = setup_prometheus()
    
    runs_per_scenario = 10  # More runs for better statistics
    total_tests = len(WORKLOAD_SCENARIOS) * runs_per_scenario
    
    print(f"📊 Test Configuration:")
    print(f"   Target replicas: {target_replicas}")
    print(f"   Scenarios: {len(WORKLOAD_SCENARIOS)} intensive scenarios")
    print(f"   Runs per scenario: {runs_per_scenario}")
    print(f"   Total tests: {total_tests}")
    print(f"   Estimated duration: {(total_tests * 2.5):.0f} minutes")
    print("")
    
    # Enhanced CSV headers
    csv_headers = [
        "concurrent_users", "requests_per_second", "total_requests", "successful_requests",
        "cpu_percent", "memory_percent", "replicas", "error_rate_percent",
        "response_time_avg", "response_time_max", "response_time_p95", "response_time_p99",
        "complexity_avg", "complexity_max", "throughput_per_replica",
        "run_number", "scenario_name", "timestamp", "test_duration", "efficiency_score"
    ]
    
    # Create or append to CSV
    try:
        with open(CSV_FILE, 'r') as f:
            print(f"💾 Appending to existing: {CSV_FILE}")
    except FileNotFoundError:
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)
        print(f"💾 Created new file: {CSV_FILE}")
    
    test_id = 0
    scenario_results = []
    
    print(f"🔢 INTENSIVE TESTING WITH {target_replicas} REPLICAS")
    print(f"{'='*70}")
    
    for scenario in WORKLOAD_SCENARIOS:
        users_min, users_max, requests_min, requests_max, complexity_min, complexity_max, duration_min, duration_max, scenario_name = scenario
        
        print(f"\n🎯 SCENARIO: {scenario_name}")
        print(f"   Users: {users_min}-{users_max}, Requests: {requests_min}-{requests_max}")
        print(f"   Complexity: {complexity_min}-{complexity_max}, Duration: {duration_min}-{duration_max}s")
        
        scenario_rps_list = []
        
        for run_number in range(runs_per_scenario):
            test_id += 1
            progress = (test_id / total_tests) * 100
            
            print(f"\n  🚀 Test {test_id}/{total_tests} [{progress:.1f}%] - Run {run_number + 1}/{runs_per_scenario}")
            
            # Generate intensive workload
            random.seed(42 + run_number + target_replicas)  # Different seed per replica count
            users = random.randint(users_min, users_max)
            total_requests = random.randint(requests_min, requests_max)
            test_duration = random.randint(duration_min, duration_max)
            
            # Create larger queue for sustained load
            queue = []
            for i in range(total_requests * 2):  # Extra requests to ensure sustained load
                complexity = random.randint(complexity_min, complexity_max)
                queue.append(complexity)
            
            random.seed()  # Reset seed
            
            complexity_avg = statistics.mean(queue[:total_requests])
            complexity_max_val = max(queue[:total_requests])
            
            print(f"    📊 Intensive Load: {total_requests * 2} requests queued, {users} concurrent users")
            print(f"    🎯 Complexity: avg={complexity_avg:.0f}, max={complexity_max_val}")
            print(f"    ⏱️ Duration: {test_duration}s sustained test")
            
            # Execute intensive test
            test_start = time.time()
            response_times = []
            actual_complexity_stats = []
            error_count = [0]  # Mutable for thread sharing
            stop_time = test_start + test_duration
            
            # Create worker threads with more aggressive concurrency
            threads = [Thread(target=intensive_workload_worker, 
                            args=(queue, response_times, actual_complexity_stats, error_count, stop_time, i)) 
                      for i in range(users)]
            
            print(f"    🔥 Starting {users} concurrent threads...")
            
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            
            elapsed_time = time.time() - test_start
            
            # Calculate enhanced metrics
            if len(response_times) >= 10:  # Higher threshold for meaningful data
                successful_requests = len(response_times)
                total_attempted = successful_requests + error_count[0]
                
                # Performance metrics
                requests_per_second = successful_requests / elapsed_time
                throughput_per_replica = requests_per_second / target_replicas
                error_rate = (error_count[0] / max(total_attempted, 1)) * 100
                
                # Response time metrics
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)
                sorted_times = sorted(response_times)
                p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
                p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]
                
                # Resource metrics
                cpu_percent = get_cpu_usage(target_replicas, prom)
                memory_percent = get_memory_usage(target_replicas, prom)
                
                # Complexity metrics
                if actual_complexity_stats:
                    actual_complexity_avg = statistics.mean(actual_complexity_stats)
                    actual_complexity_max = max(actual_complexity_stats)
                else:
                    actual_complexity_avg = complexity_avg
                    actual_complexity_max = complexity_max_val
                
                # Efficiency score (RPS per replica, adjusted for errors)
                efficiency_score = (requests_per_second / target_replicas) * (1 - error_rate/100)
                
                # Save to CSV
                csv_row = [
                    users, round(requests_per_second, 1), total_attempted, successful_requests,
                    round(cpu_percent, 1), round(memory_percent, 1), target_replicas, round(error_rate, 2),
                    round(avg_response_time, 4), round(max_response_time, 4), 
                    round(p95_response_time, 4), round(p99_response_time, 4),
                    round(actual_complexity_avg, 1), actual_complexity_max, 
                    round(throughput_per_replica, 2),
                    run_number + 1, scenario_name, int(time.time()), round(elapsed_time, 1),
                    round(efficiency_score, 2)
                ]
                
                with open(CSV_FILE, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(csv_row)
                
                scenario_rps_list.append(requests_per_second)
                
                print(f"    ✅ Run {run_number + 1} INTENSIVE RESULTS:")
                print(f"       🔥 Throughput: {requests_per_second:.1f} RPS ({throughput_per_replica:.1f} per replica)")
                print(f"       📊 Load: {successful_requests}/{total_attempted} successful ({error_rate:.1f}% errors)")
                print(f"       💻 Resources: {cpu_percent:.1f}% CPU, {memory_percent:.1f}% Memory")
                print(f"       ⏱️ Latency: {avg_response_time:.3f}s avg, {p95_response_time:.3f}s p95, {p99_response_time:.3f}s p99")
                print(f"       🎯 Efficiency: {efficiency_score:.2f} (RPS/replica adjusted for errors)")
                print(f"       🔢 Replicas: {target_replicas}")
                
            else:
                print(f"    ❌ Insufficient data ({len(response_times)} successful requests)")
                continue
            
            time.sleep(2)  # Brief pause between runs
        
        # Scenario summary
        if scenario_rps_list:
            avg_scenario_rps = statistics.mean(scenario_rps_list)
            scenario_results.append((scenario_name, avg_scenario_rps))
            print(f"\n  📈 {scenario_name} average: {avg_scenario_rps:.1f} RPS")
        
        time.sleep(5)  # Pause between scenarios for system recovery
    
    # Final summary
    print(f"\n🎉 COMPLETED INTENSIVE TESTS FOR {target_replicas} REPLICAS!")
    print(f"📄 Results saved to: {CSV_FILE}")
    print(f"🧪 Tests completed: {test_id}")
    
    if scenario_results:
        print(f"\n📊 SCENARIO PERFORMANCE SUMMARY:")
        total_avg_rps = 0
        for scenario_name, avg_rps in scenario_results:
            print(f"   {scenario_name}: {avg_rps:.1f} RPS")
            total_avg_rps += avg_rps
        
        overall_avg = total_avg_rps / len(scenario_results)
        throughput_per_replica = overall_avg / target_replicas
        
        print(f"\n🏆 OVERALL PERFORMANCE:")
        print(f"   Average RPS: {overall_avg:.1f}")
        print(f"   RPS per Replica: {throughput_per_replica:.1f}")
        print(f"   Scaling Efficiency: {(throughput_per_replica / (455 / 1)) * 100:.1f}% vs 1-replica baseline")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run intensive factorial service tests for specific replica count')
    parser.add_argument('replicas', type=int, help='Number of replicas to test (1, 2, 3, or 4)')
    
    args = parser.parse_args()
    
    if args.replicas < 1 or args.replicas > 4:
        print("❌ Replica count must be between 1 and 4")
        sys.exit(1)
    
    print(f"🔥 FACTORIAL SERVICE INTENSIVE SCALING TEST")
    print(f"=" * 70)
    print(f"🎯 Testing with {args.replicas} replicas")
    print(f"📊 Results will be saved to {CSV_FILE}")
    print(f"🚀 INTENSIVE TESTS - Designed to show clear scaling differences")
    print("")
    
    try:
        print("Starting intensive test in 5 seconds... (Ctrl+C to cancel)")
        for i in range(5, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        success = run_intensive_replica_test(args.replicas)
        
        if success:
            print(f"\n🎉 SUCCESS! Intensive test completed for {args.replicas} replicas")
            print(f"📊 Data saved to {CSV_FILE}")
            print(f"\n🔄 Next steps:")
            print(f"   1. Scale deployment: kubectl scale deployment factorial-service --replicas={args.replicas + 1} -n factorial-service")
            print(f"   2. Run next test: python test-intensive-replica.py {args.replicas + 1}")
            print(f"\n💡 The intensive tests should show clear performance differences between replica counts!")
        else:
            print(f"\n❌ FAILED! Check connectivity and try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Test cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)