#!/usr/bin/env python3
"""
Test migliorato per verificare distribuzione del carico con più concorrenza
"""
import requests
import threading
import time
from collections import Counter

def worker_thread(results, worker_id, num_requests, url):
    """Thread worker per generare carico concorrente"""
    thread_pids = []
    
    for i in range(num_requests):
        try:
            # Varia i valori di factorial per evitare caching
            factorial_val = 45 + (i % 10)  # 45-54
            test_url = url.format(factorial_val)
            
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                worker_pid = data.get('worker_pid', 'unknown')
                thread_pids.append(worker_pid)
                print(f"Thread {worker_id}, Req {i+1}: PID {worker_pid}")
            else:
                print(f"Thread {worker_id}, Req {i+1}: Error {response.status_code}")
        except Exception as e:
            print(f"Thread {worker_id}, Req {i+1}: Exception {e}")
        
        time.sleep(0.1)  # Piccola pausa tra richieste
    
    results[worker_id] = thread_pids

def test_concurrent_distribution():
    """Test con più thread concorrenti per simulare carico reale"""
    
    url = "http://127.0.0.1:51551/factorial/{}"  # UPDATE WITH YOUR URL
    
    # Configurazione test
    num_threads = 5      # Simula 5 utenti concorrenti
    requests_per_thread = 10  # 10 richieste per thread
    total_requests = num_threads * requests_per_thread
    
    print("🚀 IMPROVED LOAD BALANCING TEST")
    print("=" * 40)
    print(f"Threads (users): {num_threads}")
    print(f"Requests per thread: {requests_per_thread}")
    print(f"Total requests: {total_requests}")
    print(f"URL pattern: {url}")
    print("")
    
    # Risultati per thread
    results = {}
    threads = []
    
    # Avvia threads concorrenti
    start_time = time.time()
    
    for i in range(num_threads):
        thread = threading.Thread(
            target=worker_thread, 
            args=(results, i, requests_per_thread, url)
        )
        threads.append(thread)
        thread.start()
    
    # Aspetta completamento
    for thread in threads:
        thread.join()
    
    elapsed = time.time() - start_time
    
    # Analizza risultati
    all_pids = []
    for thread_id, pids in results.items():
        all_pids.extend(pids)
        print(f"Thread {thread_id}: {len(pids)} successful requests")
    
    print(f"\n📊 CONCURRENT LOAD ANALYSIS:")
    print(f"=" * 40)
    print(f"Total successful requests: {len(all_pids)}")
    print(f"Test duration: {elapsed:.1f} seconds")
    print(f"Average RPS: {len(all_pids) / elapsed:.1f}")
    print("")
    
    # Distribuzione worker PIDs
    pid_counts = Counter(all_pids)
    unique_workers = len(pid_counts)
    
    print(f"🎯 WORKER DISTRIBUTION:")
    print(f"Unique workers: {unique_workers}")
    
    if unique_workers > 0:
        max_requests = max(pid_counts.values())
        min_requests = min(pid_counts.values())
        imbalance_ratio = max_requests / min_requests if min_requests > 0 else float('inf')
        
        for pid, count in sorted(pid_counts.items()):
            percentage = (count / len(all_pids)) * 100
            print(f"  PID {pid}: {count:2d} requests ({percentage:5.1f}%)")
        
        print(f"\n💡 LOAD BALANCING ASSESSMENT:")
        print(f"Imbalance ratio: {imbalance_ratio:.1f}x")
        
        if imbalance_ratio <= 2.0:
            print("✅ GOOD: Load balancing is working well")
        elif imbalance_ratio <= 5.0:
            print("⚠️ MODERATE: Some imbalance but acceptable")
        else:
            print("❌ POOR: Significant load balancing issues")
        
        # Calcola efficienza teorica dello scaling
        if unique_workers > 1:
            ideal_rps_per_worker = (len(all_pids) / elapsed) / unique_workers
            print(f"\n📈 SCALING ANALYSIS:")
            print(f"Current total RPS: {len(all_pids) / elapsed:.1f}")
            print(f"RPS per unique worker: {ideal_rps_per_worker:.1f}")
            print(f"Theoretical max with perfect balancing: {ideal_rps_per_worker * unique_workers:.1f}")
            
            # Efficienza di distribuzione
            ideal_requests_per_worker = len(all_pids) / unique_workers
            actual_distribution_efficiency = min_requests / ideal_requests_per_worker
            print(f"Distribution efficiency: {actual_distribution_efficiency:.1%}")
    
    return pid_counts, elapsed, len(all_pids)

def compare_replica_scaling():
    """Confronta performance con diverse configurazioni di replica"""
    
    print(f"\n🔬 REPLICA SCALING COMPARISON")
    print("=" * 40)
    print("Testing same workload across different replica counts...")
    print("(Manually scale deployment between tests)")
    print("")
    
    results = []
    
    for test_num in range(3):  # 3 test per raccogliere dati
        input(f"📋 Test {test_num + 1}/3 - Press Enter when ready (check replica count with 'kubectl get pods -n factorial-service')...")
        
        # Ottieni numero di repliche attuali
        import subprocess
        try:
            cmd = "kubectl get deployment factorial-service -n factorial-service -o jsonpath={.status.readyReplicas}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            current_replicas = int(result.stdout.strip() or "1")
        except:
            current_replicas = int(input("Enter current replica count: "))
        
        print(f"🎯 Testing with {current_replicas} replicas...")
        
        pid_counts, elapsed, total_requests = test_concurrent_distribution()
        rps = total_requests / elapsed
        unique_workers = len(pid_counts)
        
        results.append({
            'replicas': current_replicas,
            'rps': rps,
            'unique_workers': unique_workers,
            'total_requests': total_requests,
            'duration': elapsed
        })
        
        print(f"✅ Test {test_num + 1} completed: {rps:.1f} RPS with {current_replicas} replicas")
        print("")
    
    # Analisi finale
    print(f"📊 SCALING EFFICIENCY ANALYSIS:")
    print("=" * 40)
    
    for i, result in enumerate(results):
        print(f"Test {i+1}: {result['replicas']} replicas → {result['rps']:.1f} RPS "
              f"({result['unique_workers']} unique workers)")
    
    # Calcola efficienza scaling
    if len(results) >= 2:
        baseline = results[0]
        for result in results[1:]:
            replica_ratio = result['replicas'] / baseline['replicas']
            rps_ratio = result['rps'] / baseline['rps']
            efficiency = (rps_ratio / replica_ratio) * 100
            
            print(f"\n💡 Scaling {baseline['replicas']}→{result['replicas']} replicas:")
            print(f"   Expected RPS increase: {replica_ratio:.1f}x")
            print(f"   Actual RPS increase: {rps_ratio:.1f}x")
            print(f"   Scaling efficiency: {efficiency:.1f}%")

if __name__ == "__main__":
    print("🧪 COMPREHENSIVE LOAD BALANCING TEST")
    print("=" * 50)
    print("")
    
    # Test 1: Distribuzione con carico concorrente
    test_concurrent_distribution()
    
    print("\n" + "="*50)
    
    # Test 2: Confronto scaling repliche (opzionale)
    response = input("\n🤔 Want to test replica scaling comparison? (y/n): ")
    if response.lower() == 'y':
        compare_replica_scaling()
    
    print(f"\n🎯 CONCLUSION:")
    print("If you see poor scaling efficiency, consider:")
    print("1. Using deployment port-forward instead of service")
    print("2. Adjusting service sessionAffinity settings")
    print("3. Testing with ingress controller")
    print("4. Using different load balancing algorithms")