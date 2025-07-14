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

# FIXED: Solo il primo worker avvia il server metrics
def run_metrics_server():
    """Start metrics server only in main process"""
    try:
        # Solo se è il processo principale (PID più basso o env var)
        if os.environ.get('PROMETHEUS_MULTIPROC_DIR') is None:
            start_http_server(8001)
            print("🔥 Prometheus metrics server started on port 8001")
    except OSError as e:
        if "Address already in use" in str(e):
            print("⚠️ Metrics server already running (multi-worker mode)")
        else:
            print(f"❌ Metrics server error: {e}")

# Start metrics in thread, with error handling
metrics_thread = threading.Thread(target=run_metrics_server, daemon=True)
metrics_thread.start()

def cpu_intensive_work(duration_ms=10):
    """
    Simula lavoro CPU-intensive per la durata specificata
    """
    start_time = time.time()
    target_duration = duration_ms / 1000.0  # Converti in secondi
    
    # Lavoro CPU intensivo: calcoli matematici complessi
    iterations = 0
    while (time.time() - start_time) < target_duration:
        # Operazioni matematiche costose
        for i in range(1000):
            _ = math.sin(math.sqrt(i * 3.14159)) * math.cos(i * 2.71828)
            _ = math.pow(i, 0.5) * math.log(i + 1)
        iterations += 1
    
    return iterations

def calculate_factorial_intensive(n: int) -> int:
    """
    Calcola fattoriale con stress CPU intenso REALE
    """
    if n < 0:
        return 0
    if n == 0 or n == 1:
        return 1
    
    # STRESS CPU REALE basato su n
    # Più alto n, più stress CPU
    cpu_work_duration = min(50 + (n // 10), 500)  # 50-500ms di lavoro CPU
    
    # Esegui lavoro CPU intensivo
    iterations = cpu_intensive_work(cpu_work_duration)
    
    # Calcolo fattoriale con operazioni aggiuntive costose
    result = 1
    for i in range(2, n + 1):
        result *= i
        
        # Aggiungi operazioni costose ogni 50 iterazioni
        if i % 50 == 0:
            # Simula validazioni complesse
            _ = math.sqrt(result % (10**10)) * math.pi
            time.sleep(0.001)  # Micro-sleep per stress aggiuntivo
    
    return result

def advanced_factorial_analysis(result: int, n: int):
    """
    Analisi avanzata del fattoriale (CPU intensive)
    """
    analysis = {}
    
    # Conta cifre (operazione costosa per numeri grandi)
    digit_count = 0
    temp_result = result
    while temp_result > 0:
        digit_count += 1
        temp_result //= 10
    
    analysis['factorial_digits'] = digit_count
    
    # Analisi proprietà matematiche (costose)
    analysis['is_even'] = (result % 2 == 0)
    analysis['last_digit'] = result % 10
    analysis['digit_sum'] = sum(int(digit) for digit in str(result)[:100])  # Prime 100 cifre
    
    # Analisi divisibilità (CPU intensive)
    divisibility_tests = [3, 5, 7, 11, 13]
    analysis['divisible_by'] = [d for d in divisibility_tests if result % d == 0]
    
    # Calcoli statistici sulle cifre
    digits = [int(d) for d in str(result)[:1000]]  # Prime 1000 cifre
    if digits:
        analysis['digit_mean'] = sum(digits) / len(digits)
        analysis['digit_variance'] = sum((d - analysis['digit_mean'])**2 for d in digits) / len(digits)
    
    return analysis

@app.get("/factorial/{n}")
def compute_factorial(n: int):
    """Endpoint per calcolo fattoriale CPU-INTENSIVE"""
    if n < 0:
        raise HTTPException(status_code=400, detail="Number must be non-negative")
    if n > 5000:  # Aumentato limite per stress test
        raise HTTPException(status_code=400, detail="Number too large (max 5000)")
    
    REQ_COUNTER.inc()
    IN_PROGRESS.inc()
    start = time.time()
    
    try:
        # Calcolo fattoriale CPU-intensive
        result = calculate_factorial_intensive(n)
        computation_time = time.time() - start
        
        if n > 50:
            # Analisi avanzata CPU-intensive
            analysis = advanced_factorial_analysis(result, n)
            
            response = {
                "number": n,
                "computation_time": computation_time,
                "cpu_intensive": True,
                "worker_pid": os.getpid(),  # Debug: mostra quale worker ha risposto
                **analysis,
                "note": f"CPU-intensive factorial computed in {computation_time:.3f}s by worker {os.getpid()}"
            }
        else:
            response = {
                "number": n, 
                "factorial": result,
                "computation_time": computation_time,
                "cpu_intensive": False,
                "worker_pid": os.getpid()
            }
        
        return response
    
    finally:
        elapsed = time.time() - start
        LATENCY.observe(elapsed)
        IN_PROGRESS.dec()

# Mantieni endpoint compatibile
@app.get("/prime/{n}")  
def prime_compatibility(n: int):
    """Endpoint di compatibilità - calcola factorial CPU-intensive"""
    return compute_factorial(n)

@app.get("/")
def root():
    return {
        "service": "Multi-Worker CPU-Intensive Factorial Service", 
        "description": "Realistic CPU-intensive factorial calculations with multi-worker support",
        "worker_pid": os.getpid(),
        "cpu_work": "50-500ms per request based on input size",
        "endpoints": {
            "/factorial/{n}": "Calculate CPU-intensive factorial",
            "/prime/{n}": "Compatibility endpoint (calculates factorial)"
        }
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "factorial-service",
        "worker_pid": os.getpid()
    }