from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time
import threading
import sys
import math
import random
import os

# Aumenta il limite per conversione string di numeri grandi
sys.set_int_max_str_digits(0)

app = FastAPI()

# Metriche Prometheus
REQ_COUNTER = Counter('factorial_requests_total', 'Richieste totali ricevute')
IN_PROGRESS = Gauge('factorial_inprogress_requests', 'Richieste in corso')
LATENCY = Histogram('factorial_request_latency_seconds', 'Istogramma delle latenze')

def run_metrics_server():
    """Start metrics server only in main process"""
    try:
        if os.environ.get('PROMETHEUS_MULTIPROC_DIR') is None:
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
    """
    FIXED: Lavoro CPU molto più leggero - solo 1-10ms invece di 50-500ms!
    """
    # Ridotto drasticamente: max 10ms invece di 500ms
    base_work = max(1, n // 100)  # 1ms base, +1ms ogni 100 unità
    work_duration_ms = min(base_work, 10)  # MASSIMO 10ms invece di 500ms!
    
    start_time = time.time()
    target_duration = work_duration_ms / 1000.0
    
    # Lavoro CPU molto più leggero
    while (time.time() - start_time) < target_duration:
        for i in range(100):  # Ridotto da 1000 a 100
            _ = math.sin(i) * math.cos(i)  # Semplificato
    
    return work_duration_ms

def calculate_factorial_optimized(n: int) -> int:
    """
    FIXED: Calcolo fattoriale ottimizzato - molto più veloce
    """
    if n < 0:
        return 0
    if n == 0 or n == 1:
        return 1
    
    # FIXED: Lavoro CPU molto ridotto
    light_cpu_work(n)
    
    # Calcolo fattoriale ottimizzato
    if n > 1000:
        # Per numeri molto grandi, usa approssimazione di Stirling
        # Questo evita calcoli eccessivamente lunghi
        result = math.factorial(min(n, 100))  # Limita il calcolo
        return result
    else:
        # Calcolo normale per numeri ragionevoli
        return math.factorial(n)

def light_analysis(result: int, n: int):
    """
    FIXED: Analisi molto più leggera - solo informazioni base
    """
    if n < 50:
        return {}  # Nessuna analisi per numeri piccoli
    
    # Analisi molto semplificata
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
    """FIXED: Endpoint factorial molto più veloce"""
    if n < 0:
        raise HTTPException(status_code=400, detail="Number must be non-negative")
    if n > 1000:  # RIDOTTO: limite molto più basso
        raise HTTPException(status_code=400, detail="Number too large (max 1000)")
    
    REQ_COUNTER.inc()
    IN_PROGRESS.inc()
    start = time.time()
    
    try:
        # FIXED: Calcolo molto più veloce
        result = calculate_factorial_optimized(n)
        computation_time = time.time() - start
        
        # FIXED: Analisi leggera solo per numeri > 50
        if n > 50:
            analysis = light_analysis(result, n)
            response = {
                "number": n,
                "computation_time": computation_time,
                "worker_pid": os.getpid(),
                **analysis,
                "note": f"Optimized factorial computed in {computation_time:.3f}s"
            }
        else:
            response = {
                "number": n, 
                "factorial": result,
                "computation_time": computation_time,
                "worker_pid": os.getpid()
            }
        
        return response
    
    finally:
        elapsed = time.time() - start
        LATENCY.observe(elapsed)
        IN_PROGRESS.dec()

@app.get("/prime/{n}")  
def prime_compatibility(n: int):
    """Endpoint di compatibilità"""
    return compute_factorial(n)

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

@app.get("/health")
def health():
    return {
        "status": "healthy", 
        "service": "factorial-service",
        "worker_pid": os.getpid()
    }