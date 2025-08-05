#!/usr/bin/env python3
"""
Service-Only Test - Verifica load balancing attraverso service
(Pod IP non raggiungibili dal PC, solo dal cluster)
"""

import requests
import time
from collections import defaultdict
import threading

SERVICE_API = "http://192.168.1.240:30080/factorial/{}"

def extended_load_balancing_test():
    """Test esteso per verificare distribuzione load balancing"""
    
    print("🌐 EXTENDED LOAD BALANCING TEST")
    print("=" * 50)
    print("Testing through service only (pod IPs not reachable from PC)")
    print("")
    
    # Test con diversi pattern per forzare distribuzione
    test_patterns = [
        ("Sequential", range(1, 101)),           # 1-100
        ("Random-like", [i*7 % 97 + 10 for i in range(100)]),  # Pattern semi-random
        ("Burst", [50] * 100),                   # Stesso valore
    ]
    
    all_results = {}
    
    for pattern_name, values in test_patterns:
        print(f"🎯 Pattern: {pattern_name}")
        
        worker_pids = []
        failed_requests = 0
        
        start_time = time.time()
        
        for i, value in enumerate(values):
            try:
                response = requests.get(SERVICE_API.format(value), timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    worker_pid = data.get('worker_pid', 'unknown')
                    worker_pids.append(worker_pid)
                else:
                    failed_requests += 1
            except Exception:
                failed_requests += 1
            
            # Progress ogni 25 richieste
            if (i + 1) % 25 == 0:
                print(f"   Progress: {i+1}/100")
        
        elapsed = time.time() - start_time
        
        # Analisi risultati
        pid_counts = defaultdict(int)
        for pid in worker_pids:
            pid_counts[pid] += 1
        
        successful = len(worker_pids)
        unique_pids = len(pid_counts)
        
        print(f"   ✅ Successful: {successful}/100, Failed: {failed_requests}")
        print(f"   🎯 Unique Worker PIDs: {unique_pids}")
        print(f"   ⏱️ Duration: {elapsed:.1f}s, RPS: {successful/elapsed:.1f}")
        
        # Distribuzione dettagliata
        print(f"   📊 PID Distribution:")
        for pid, count in sorted(pid_counts.items()):
            percentage = (count / successful) * 100 if successful > 0 else 0
            print(f"      Worker PID {pid}: {count} requests ({percentage:.1f}%)")
        
        all_results[pattern_name] = {
            'unique_pids': unique_pids,
            'successful': successful,
            'rps': successful/elapsed if elapsed > 0 else 0,
            'distribution': dict(pid_counts)
        }
        
        print()
        time.sleep(2)  # Pausa tra pattern
    
    return all_results

def concurrent_load_test():
    """Test con richieste concorrenti per stressare il load balancer"""
    
    print("🚀 CONCURRENT LOAD TEST")
    print("=" * 30)
    
    results = []
    lock = threading.Lock()
    
    def worker_thread(thread_id, num_requests):
        thread_results = []
        for i in range(num_requests):
            try:
                value = 100 + thread_id * 10 + i  # Valore unico per thread
                response = requests.get(SERVICE_API.format(value), timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    worker_pid = data.get('worker_pid', 'unknown')
                    thread_results.append(worker_pid)
            except Exception:
                continue
        
        with lock:
            results.extend(thread_results)
            print(f"   Thread {thread_id}: {len(thread_results)} requests completed")
    
    # Test con 15 thread, 20 richieste ciascuno = 300 richieste totali
    num_threads = 15
    requests_per_thread = 20
    
    print(f"🎯 Starting {num_threads} threads × {requests_per_thread} requests = {num_threads * requests_per_thread} total")
    
    start_time = time.time()
    
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=worker_thread, args=(i, requests_per_thread))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    elapsed = time.time() - start_time
    
    # Analisi risultati concorrenti
    pid_counts = defaultdict(int)
    for pid in results:
        pid_counts[pid] += 1
    
    total_requests = len(results)
    unique_pids = len(pid_counts)
    rps = total_requests / elapsed
    
    print(f"\n📊 CONCURRENT RESULTS:")
    print(f"   📈 Total Requests: {total_requests}")  
    print(f"   🔥 RPS: {rps:.1f}")
    print(f"   🎯 Unique Worker PIDs: {unique_pids}")
    print(f"   ⏱️ Duration: {elapsed:.1f}s")
    
    print(f"\n🔄 LOAD DISTRIBUTION:")
    for pid, count in sorted(pid_counts.items()):
        percentage = (count / total_requests) * 100
        print(f"   Worker PID {pid}: {count} requests ({percentage:.1f}%)")
    
    return {
        'unique_pids': unique_pids,
        'total_requests': total_requests,
        'rps': rps
    }

if __name__ == "__main__":
    print("🔍 SERVICE LOAD BALANCING VERIFICATION")
    print("=" * 60)
    print("Note: Testing only through service (pod IPs not reachable from PC)")
    print("")
    
    # Test 1: Pattern diversi
    pattern_results = extended_load_balancing_test()
    
    # Test 2: Carico concorrente
    concurrent_result = concurrent_load_balancing_test()
    
    # Analisi finale
    print(f"\n🏆 FINAL ASSESSMENT:")
    print("=" * 30)
    
    max_pids = max(r['unique_pids'] for r in pattern_results.values())
    max_rps = max(r['rps'] for r in pattern_results.values())
    concurrent_pids = concurrent_result['unique_pids']
    concurrent_rps = concurrent_result['rps']
    
    print(f"📊 Pattern Tests:")
    print(f"   Max Unique PIDs: {max_pids}")
    print(f"   Max RPS: {max_rps:.1f}")
    
    print(f"\n🚀 Concurrent Test:")
    print(f"   Unique PIDs: {concurrent_pids}")
    print(f"   RPS: {concurrent_rps:.1f}")
    
    # Valutazione con 3 pod (attesi: 8-12 worker PIDs)
    expected_min = 8   # 3 pod × ~3 worker visibili
    expected_max = 12  # 3 pod × 4 worker
    
    best_pids = max(max_pids, concurrent_pids)
    
    print(f"\n🎯 SCALING ASSESSMENT (3 pods):")
    print(f"   Expected Worker PIDs: {expected_min}-{expected_max}")
    print(f"   Detected Worker PIDs: {best_pids}")
    
    if best_pids >= expected_min:
        efficiency = min(100, (best_pids / expected_max) * 100)
        print(f"   ✅ Load balancing working: {efficiency:.1f}% efficiency")
        print(f"   📈 All 3 pods are likely receiving traffic")
    else:
        print(f"   ⚠️ Partial load balancing: Only ~{best_pids//4} pods active")
        print(f"   💡 Some pods might not be receiving traffic")
    
    print(f"\n🔥 Peak Performance: {max(max_rps, concurrent_rps):.1f} RPS")