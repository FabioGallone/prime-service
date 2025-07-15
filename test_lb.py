# Salva questo come test_lb.py
import requests
import time
from collections import Counter

def test_load_balancing():
    url = "http://localhost/factorial/50"
    
    print("🧪 Testing load balancing...")
    print(f"URL: {url}")
    print("Making 30 requests to check PID distribution...\n")
    
    worker_pids = []
    
    for i in range(30):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                worker_pid = data.get('worker_pid', 'unknown')
                worker_pids.append(worker_pid)
                print(f"Request {i+1:2d}: Worker PID {worker_pid}")
            else:
                print(f"Request {i+1:2d}: Error {response.status_code}")
        except Exception as e:
            print(f"Request {i+1:2d}: Exception {e}")
        
        time.sleep(0.1)  # Small delay
    
    # Analyze distribution
    print(f"\n📊 LOAD BALANCING ANALYSIS:")
    print(f"Total successful requests: {len(worker_pids)}")
    
    if len(worker_pids) == 0:
        print("❌ No successful requests!")
        return False
    
    pid_counts = Counter(worker_pids)
    unique_pids = len(pid_counts)
    
    print(f"Unique worker PIDs: {unique_pids}")
    
    for pid, count in pid_counts.items():
        percentage = (count / len(worker_pids)) * 100
        print(f"  PID {pid}: {count} requests ({percentage:.1f}%)")
    
    # Load balancing assessment
    if unique_pids == 1:
        print(f"\n❌ LOAD BALANCING FAILED")
        print(f"   All requests go to same worker (PID {list(pid_counts.keys())[0]})")
        print(f"   This explains poor scaling efficiency!")
        return False
    
    elif unique_pids >= 2:
        values = list(pid_counts.values())
        max_requests = max(values)
        min_requests = min(values)
        imbalance_ratio = max_requests / min_requests if min_requests > 0 else float('inf')
        
        if imbalance_ratio <= 3.0:
            print(f"\n✅ LOAD BALANCING WORKING")
            print(f"   Good distribution across {unique_pids} workers")
            print(f"   Imbalance ratio: {imbalance_ratio:.1f}x (acceptable)")
            return True
        else:
            print(f"\n⚠️ LOAD BALANCING POOR")
            print(f"   High imbalance ratio: {imbalance_ratio:.1f}x")
            print(f"   Some workers get much more traffic")
            return False

if __name__ == "__main__":
    test_load_balancing()