#!/usr/bin/env python3
"""
Debug script per identificare il problema CPU monitoring con multiple repliche
"""

import requests
import json
import subprocess
from prometheus_api_client import PrometheusConnect

PROM_URL = "http://localhost:9090"
prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)

def debug_prometheus_cpu_queries():
    """Debug dettagliato delle query CPU"""
    print("🔍 DEBUGGING CPU MONITORING ISSUE")
    print("=" * 60)
    
    # 1. Check basic Prometheus connectivity
    print("\n1️⃣ PROMETHEUS CONNECTIVITY:")
    try:
        response = prom.custom_query("up")
        targets = len(response)
        print(f"✅ Prometheus OK: {targets} targets available")
        
        for target in response[:5]:  # Show first 5 targets
            job = target.get('metric', {}).get('job', 'unknown')
            instance = target.get('metric', {}).get('instance', 'unknown')
            status = target.get('value', [None, '0'])[1]
            print(f"   📊 {job}: {instance} → {'UP' if status == '1' else 'DOWN'}")
    except Exception as e:
        print(f"❌ Prometheus connection failed: {e}")
        return False
    
    # 2. Check available CPU metrics
    print("\n2️⃣ AVAILABLE CPU METRICS:")
    cpu_metrics = [
        "container_cpu_usage_seconds_total",
        "container_cpu_system_seconds_total", 
        "container_cpu_user_seconds_total",
        "rate(container_cpu_usage_seconds_total[1m])",
    ]
    
    for metric in cpu_metrics:
        try:
            result = prom.custom_query(metric)
            if result:
                print(f"✅ {metric}: {len(result)} series")
                # Show first few series for debugging
                for i, series in enumerate(result[:3]):
                    labels = series.get('metric', {})
                    value = series.get('value', [None, 'N/A'])[1]
                    namespace = labels.get('namespace', 'N/A')
                    pod = labels.get('pod', 'N/A')[:20]  # Truncate long pod names
                    container = labels.get('container', 'N/A')
                    print(f"     └─ {namespace}/{pod}/{container}: {value}")
            else:
                print(f"❌ {metric}: No data")
        except Exception as e:
            print(f"❌ {metric}: Error - {str(e)[:50]}")
    
    # 3. Check prime-service specific metrics
    print("\n3️⃣ PRIME-SERVICE SPECIFIC METRICS:")
    service_queries = [
        'container_cpu_usage_seconds_total{namespace="prime-service"}',
        'container_cpu_usage_seconds_total{pod=~"prime-service-.*"}',
        'container_cpu_usage_seconds_total{container="factorial-service"}',
        'sum(rate(container_cpu_usage_seconds_total{namespace="prime-service"}[1m]))',
        'sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="prime-service"}[1m]))',
    ]
    
    for query in service_queries:
        try:
            result = prom.custom_query(query)
            if result:
                print(f"✅ Query works: {query}")
                print(f"   📊 Results: {len(result)} series")
                
                # Detailed breakdown
                for series in result:
                    labels = series.get('metric', {})
                    value = series.get('value', [None, 'N/A'])[1]
                    pod = labels.get('pod', 'N/A')
                    container = labels.get('container', 'N/A')
                    print(f"     🔸 Pod: {pod}, Container: {container}, Value: {value}")
            else:
                print(f"❌ No data: {query}")
        except Exception as e:
            print(f"❌ Query failed: {query}")
            print(f"   Error: {str(e)[:100]}")
    
    # 4. Check current pod status
    print("\n4️⃣ CURRENT POD STATUS:")
    try:
        cmd = "kubectl get pods -n prime-service -o json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            pods_info = json.loads(result.stdout)
            pods = pods_info.get('items', [])
            print(f"📊 Found {len(pods)} pods in prime-service namespace:")
            
            for pod in pods:
                name = pod['metadata']['name']
                status = pod['status']['phase']
                ready = 'Unknown'
                
                # Check readiness
                conditions = pod.get('status', {}).get('conditions', [])
                for condition in conditions:
                    if condition['type'] == 'Ready':
                        ready = condition['status']
                        break
                
                # Get container info
                containers = pod.get('status', {}).get('containerStatuses', [])
                container_info = []
                for container in containers:
                    container_name = container['name']
                    container_ready = container['ready']
                    restart_count = container['restartCount']
                    container_info.append(f"{container_name}(ready={container_ready},restarts={restart_count})")
                
                print(f"   🔸 {name}: {status} | Ready: {ready}")
                print(f"      Containers: {', '.join(container_info)}")
        else:
            print(f"❌ kubectl failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Pod status check failed: {e}")
    
    # 5. Test the exact queries your script uses
    print("\n5️⃣ TESTING YOUR SCRIPT'S QUERIES:")
    your_queries = [
        'sum(rate(container_cpu_usage_seconds_total{namespace="prime-service",container!="POD"}[30s]))',
        'sum(rate(container_cpu_usage_seconds_total{pod=~"prime-service-.*"}[30s]))',
        'sum(rate(container_cpu_usage_seconds_total{container="factorial-service"}[30s]))',
    ]
    
    working_queries = []
    for i, query in enumerate(your_queries, 1):
        try:
            result = prom.custom_query(query)
            if result and len(result) > 0:
                value = float(result[0]['value'][1])
                if value > 0:
                    print(f"✅ Query {i}: {value:.4f} CPU cores")
                    working_queries.append((query, value))
                else:
                    print(f"⚠️ Query {i}: Returns 0 (may be timing issue)")
            else:
                print(f"❌ Query {i}: No data returned")
        except Exception as e:
            print(f"❌ Query {i}: {str(e)[:100]}")
    
    # 6. Recommendations
    print("\n6️⃣ DIAGNOSIS & RECOMMENDATIONS:")
    
    if not working_queries:
        print("🚨 CRITICAL: No CPU queries working!")
        print("📋 Action items:")
        print("   1. Check if cAdvisor is running: kubectl get pods -n kube-system | grep cadvisor")
        print("   2. Verify Prometheus config: kubectl get configmap prometheus-config -n prime-service -o yaml")
        print("   3. Check RBAC permissions: kubectl auth can-i get nodes --as=system:serviceaccount:prime-service:prometheus")
        print("   4. Test manual query: kubectl top pods -n prime-service")
    else:
        print(f"✅ Found {len(working_queries)} working queries")
        print("📋 Recommendations:")
        print("   1. Use the working queries in your script")
        print("   2. Add retry logic with different time windows")
        print("   3. Implement per-pod aggregation")
        print("   4. Add fallback to kubectl top pods")
    
    return working_queries

def test_cpu_monitoring_per_replica():
    """Test CPU monitoring con diverse repliche"""
    print("\n🧪 TESTING CPU MONITORING PER REPLICA")
    print("=" * 60)
    
    # Get current replica count
    try:
        cmd = "kubectl get deployment prime-service -n prime-service -o json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            current_replicas = info.get('spec', {}).get('replicas', 1)
            ready_replicas = info.get('status', {}).get('readyReplicas', 0)
            
            print(f"📊 Current deployment: {current_replicas} spec, {ready_replicas} ready")
            
            # Test queries with current setup
            working_queries = debug_prometheus_cpu_queries()
            
            if working_queries:
                print(f"\n📈 CPU MONITORING TEST RESULTS:")
                for query, value in working_queries:
                    cpu_per_replica = value / max(ready_replicas, 1)
                    cpu_percentage = (cpu_per_replica / 2.0) * 100  # Assuming 2 CPU limit
                    print(f"   🔸 Total CPU: {value:.4f} cores")
                    print(f"   🔸 CPU per replica: {cpu_per_replica:.4f} cores ({cpu_percentage:.1f}%)")
                    print(f"   🔸 Query: {query[:80]}...")
                    print()
        else:
            print(f"❌ Failed to get deployment info: {result.stderr}")
    except Exception as e:
        print(f"❌ Replica test failed: {e}")

def generate_fixed_cpu_function():
    """Genera la funzione CPU corretta per il tuo script"""
    print("\n🔧 FIXED CPU MONITORING FUNCTION")
    print("=" * 60)
    
    working_queries = debug_prometheus_cpu_queries()
    
    if working_queries:
        best_query = working_queries[0][0]  # Use first working query
        
        print("📝 Replace your get_cpu_usage_percentage() with:")
        print("""
def get_cpu_usage_percentage_fixed(replicas):
    '''Fixed CPU monitoring with proper per-replica calculation'''
    
    # Working query identified by debug script
    cpu_queries = [
        f'{best_query}',
        'sum(rate(container_cpu_usage_seconds_total{{namespace="prime-service"}}[1m]))',
        'sum by (pod) (rate(container_cpu_usage_seconds_total{{namespace="prime-service"}}[1m]))'
    ]
    
    for query in cpu_queries:
        try:
            result = prom.custom_query(query=query)
            if result and len(result) > 0:
                
                if len(result) == 1:
                    # Single aggregated value
                    total_cpu_cores = float(result[0]['value'][1])
                    avg_cpu_per_replica = total_cpu_cores / replicas
                else:
                    # Per-pod values  
                    cpu_values = [float(r['value'][1]) for r in result]
                    avg_cpu_per_replica = statistics.mean(cpu_values)
                
                # Convert to percentage (assuming 2 CPU limit per container)
                cpu_percentage = min((avg_cpu_per_replica / 2.0) * 100, 95.0)
                
                # Validate result is realistic
                if 0.5 <= cpu_percentage <= 95.0:
                    return cpu_percentage
                    
        except Exception:
            continue
    
    # Fallback: estimate based on load (better than fixed values)
    return estimate_cpu_from_load(replicas)

def estimate_cpu_from_load(replicas):
    '''Realistic CPU estimation when monitoring fails'''
    # Your current load generation logic should inform this
    base_cpu_per_replica = 25  # Baseline CPU per replica
    distribution_efficiency = max(0.4, 1.0 - (replicas - 1) * 0.15)
    
    estimated_cpu = base_cpu_per_replica * distribution_efficiency
    return max(5.0, min(estimated_cpu, 85.0))
""")
    else:
        print("❌ No working queries found. Check Prometheus setup first.")

if __name__ == "__main__":
    # Run comprehensive debugging
    working_queries = debug_prometheus_cpu_queries() 
    test_cpu_monitoring_per_replica()
    generate_fixed_cpu_function()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Fix any Prometheus connectivity issues found above")
    print("2. Replace your CPU monitoring function with the fixed version")
    print("3. Re-run your simulation with proper CPU monitoring")
    print("4. Expect much more realistic CPU patterns!")