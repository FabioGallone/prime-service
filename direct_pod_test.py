#!/usr/bin/env python3
"""
Test diretto ai pod individuali per verificare che abbiano worker diversi
"""

import requests
import subprocess
import time
import json

def get_pod_ips():
    """Ottieni IP dei pod"""
    try:
        cmd = [
            'kubectl', 'get', 'pods', '-n', 'factorial-service', 
            '-l', 'app=factorial-service',
            '-o', 'jsonpath={.items[*].status.podIP}'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        pod_ips = result.stdout.strip().split()
        
        cmd_names = [
            'kubectl', 'get', 'pods', '-n', 'factorial-service', 
            '-l', 'app=factorial-service',
            '-o', 'jsonpath={.items[*].metadata.name}'
        ]
        result_names = subprocess.run(cmd_names, capture_output=True, text=True)
        pod_names = result_names.stdout.strip().split()
        
        return list(zip(pod_names, pod_ips))
        
    except Exception as e:
        print(f"Error getting pod IPs: {e}")
        return []

def test_pod_direct(pod_name, pod_ip):
    """Test diretto a un pod specifico"""
    
    print(f"\n🧪 Testing pod {pod_name} ({pod_ip})")
    print("-" * 40)
    
    # Port-forward to specific pod
    print(f"Setting up port-forward to {pod_name}...")
    
    # Use kubectl port-forward to specific pod
    port = 8100 + hash(pod_name) % 100  # Unique port per pod
    
    try:
        # Start port-forward in background
        import subprocess
        import threading
        
        cmd = [
            'kubectl', 'port-forward', '-n', 'factorial-service',
            f'pod/{pod_name}', f'{port}:8000'
        ]
        
        def run_portforward():
            subprocess.run(cmd, capture_output=True)
        
        pf_thread = threading.Thread(target=run_portforward, daemon=True)
        pf_thread.start()
        
        # Wait for port-forward to be ready
        time.sleep(3)
        
        # Test the pod
        workers = []
        for i in range(10):
            try:
                response = requests.get(f"http://localhost:{port}/factorial/{40+i}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    worker_pid = data.get('worker_pid', 'unknown')
                    workers.append(worker_pid)
                    
                    if i == 0:
                        print(f"  ✅ Pod responsive - Worker PID: {worker_pid}")
                        
            except Exception as e:
                if i == 0:
                    print(f"  ❌ Pod not accessible: {e}")
                break
            
            time.sleep(0.1)
        
        if workers:
            unique_workers = set(workers)
            print(f"  📊 Workers in this pod: {unique_workers}")
            print(f"  🔢 Total unique workers: {len(unique_workers)}")
            return unique_workers
        else:
            print(f"  ❌ No successful requests to {pod_name}")
            return set()
            
    except Exception as e:
        print(f"  ❌ Error testing {pod_name}: {e}")
        return set()

def analyze_service_vs_pods():
    """Analizza differenza tra service e pod diretti"""
    
    print("🔍 DIRECT POD ANALYSIS")
    print("=" * 30)
    
    # Get pod information
    pods = get_pod_ips()
    if not pods:
        print("❌ Could not get pod information")
        return
    
    print(f"Found {len(pods)} pods:")
    for name, ip in pods:
        print(f"  📍 {name}: {ip}")
    
    # Test each pod directly
    all_workers = set()
    pod_workers = {}
    
    for pod_name, pod_ip in pods:
        workers = test_pod_direct(pod_name, pod_ip)
        pod_workers[pod_name] = workers
        all_workers.update(workers)
    
    # Summary
    print(f"\n📊 ANALYSIS SUMMARY:")
    print("=" * 25)
    
    total_unique_workers = len(all_workers)
    print(f"Total unique workers across all pods: {total_unique_workers}")
    print(f"All worker PIDs: {sorted(all_workers)}")
    
    for pod_name, workers in pod_workers.items():
        print(f"Pod {pod_name}: {len(workers)} workers {sorted(workers)}")
    
    # Diagnosis
    print(f"\n💡 DIAGNOSIS:")
    if total_unique_workers >= len(pods) * 2:
        print("✅ Pods have multiple workers each - this is good!")
        print("❌ Service load balancing is the issue")
    elif total_unique_workers > 1:
        print("⚠️ Some workers available but limited")
        print("🔍 May be configuration or deployment issue")
    else:
        print("❌ Only one worker across all pods")
        print("🔍 This is a deployment or container issue")
    
    return pod_workers, all_workers

def main():
    print("🔍 DIRECT POD WORKER ANALYSIS")
    print("=" * 35)
    print("Testing each pod individually to understand worker distribution")
    print("")
    
    pod_workers, all_workers = analyze_service_vs_pods()
    
    print(f"\n🎯 CONCLUSIONS:")
    if len(all_workers) > 2:
        print("✅ Multiple workers exist - service routing is the issue")
        print("💡 Consider using deployment port-forward for simulation")
        print("📝 Document that load balancing is a service-level limitation")
    elif len(all_workers) > 1:
        print("⚠️ Limited workers available")
        print("💡 May still get some scaling benefit")
    else:
        print("❌ Single worker across all infrastructure") 
        print("🔍 This explains poor scaling efficiency")

if __name__ == "__main__":
    main()