from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time
import threading
import sys
import math
import random
import os

# Rimuove il limite per conversione string di numeri grandi
sys.set_int_max_str_digits(0)

app = FastAPI()

# Metriche Prometheus
REQ_COUNTER = Counter('factorial_requests_total', 'Richieste totali ricevute')
IN_PROGRESS = Gauge('factorial_inprogress_requests', 'Richieste in corso')
LATENCY = Histogram('factorial_request_latency_seconds', 'Istogramma delle latenze')

def run_metrics_server():
    try:
        if os.environ.get('PROMETHEUS_MULTIPROC_DIR') is None:
            #Avvia il server per metriche su porta 8001
            start_http_server(8001)
            print("🔥 Prometheus metrics server started on port 8001")
    except OSError as e:
        if "Address already in use" in str(e):
            print("⚠️ Metrics server already running (multi-worker mode)")
        else:
            print(f"❌ Metrics server error: {e}")

metrics_thread = threading.Thread(target=run_metrics_server, daemon=True)
metrics_thread.start()

def light_cpu_work(n: int):
    base_work = max(1, n // 100)  # 1ms base, +1ms ogni 100 unità (carico minimo)
    work_duration_ms = min(base_work, 10)  # MASSIMO 10ms di lavoro CPU
    
    start_time = time.time()
    target_duration = work_duration_ms / 1000.0
    

    while (time.time() - start_time) < target_duration:
        for i in range(100): 
            _ = math.sin(i) * math.cos(i)  # Operazioni trigonometriche "leggere"
    
    return work_duration_ms

def calculate_factorial_optimized(n: int) -> int:
    # 0!=1, 1!=1
    if n < 0:
        return 0
    if n == 0 or n == 1:
        return 1

    light_cpu_work(n)

    return math.factorial(n)

def light_analysis(result: int, n: int):

    if n < 50:
        return {}  # Nessuna analisi per numeri piccoli
    
    # Analisi
    result_str = str(result)
    analysis = {
        'digit_count': len(result_str),
        'is_even': (result % 2 == 0),
        'last_digit': result % 10,
        'first_digits': result_str[:5] if len(result_str) > 5 else result_str 
    }
    
    return analysis

@app.get("/factorial/{n}")
def compute_factorial(n: int):
    if n < 0:
        raise HTTPException(status_code=400, detail="Number must be non-negative")
    if n > 1500:  
        raise HTTPException(status_code=400, detail="Number too large (max 1500)")
    
    REQ_COUNTER.inc()
    IN_PROGRESS.inc()
    start = time.time()
    
    try:
        result = calculate_factorial_optimized(n)
        computation_time = time.time() - start
        
        worker_pid = os.getpid()
        
        response = {
            "number": n,
            "computation_time": computation_time,
            "worker_pid": worker_pid
        }
        
        # Aggiungi factorial per numeri piccoli, nella risposta HTTP
        if n <= 50:
            response["factorial"] = result
        
        # Analisi leggera solo per numeri > 50
        if n > 50:
            analysis = light_analysis(result, n)
            response.update(analysis)
            response["note"] = f"Optimized factorial computed in {computation_time:.3f}s"
        
        return response
    
    finally:
        elapsed = time.time() - start
        LATENCY.observe(elapsed)
        IN_PROGRESS.dec()


#JSON di benvenuto che spiega di cosa si tratta
@app.get("/")
def root():
    return {
        "service": "Optimized Factorial Service", 
        "description": "Fast factorial calculations with reasonable CPU usage",
        "worker_pid": os.getpid(),
        "cpu_work": "1-10ms per request (optimized)",
        "endpoints": {
            "/factorial/{n}": "Calculate optimized factorial",
            "/prime/{n}": "Compatibility endpoint"
        }
    }
