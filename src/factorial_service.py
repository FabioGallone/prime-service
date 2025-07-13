from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time
import threading

app = FastAPI()

# Metriche Prometheus
REQ_COUNTER = Counter('factorial_requests_total', 'Richieste totali ricevute')
IN_PROGRESS = Gauge('factorial_inprogress_requests', 'Richieste in corso')
LATENCY = Histogram('factorial_request_latency_seconds', 'Istogramma delle latenze')

def run_metrics_server():
    start_http_server(8001)

threading.Thread(target=run_metrics_server, daemon=True).start()

def calculate_factorial(n: int) -> int:
    """
    Calcola fattoriale con stress CPU intenso
    Metodo iterativo per massimo stress
    """
    if n < 0:
        return 0
    if n == 0 or n == 1:
        return 1
    
    # Calcolo iterativo per stress CPU massimo
    result = 1
    for i in range(2, n + 1):
        result *= i
    
    return result

@app.get("/factorial/{n}")
def compute_factorial(n: int):
    """Endpoint per calcolo fattoriale"""
    if n < 0:
        raise HTTPException(status_code=400, detail="Number must be non-negative")
    if n > 50000:  # Limite per evitare timeout
        raise HTTPException(status_code=400, detail="Number too large (max 50000)")
    
    REQ_COUNTER.inc()
    IN_PROGRESS.inc()
    start = time.time()
    
    try:
        result = calculate_factorial(n)
        elapsed = time.time() - start
        
        # Per numeri grandi, restituiamo solo info sulla dimensione
        if result > 10**100:  # Numeri molto grandi
            result_str = str(result)
            return {
                "number": n, 
                "factorial_digits": len(result_str),
                "first_20_digits": result_str[:20],
                "last_20_digits": result_str[-20:],
                "computation_time": elapsed
            }
        else:
            return {
                "number": n, 
                "factorial": result,
                "computation_time": elapsed
            }
    
    finally:
        elapsed = time.time() - start
        LATENCY.observe(elapsed)
        IN_PROGRESS.dec()

# Mantieni endpoint compatibile con monitoring
@app.get("/prime/{n}")  
def prime_compatibility(n: int):
    """Endpoint di compatibilità - calcola factorial invece di prime"""
    return compute_factorial(n)

@app.get("/")
def root():
    return {
        "service": "Factorial Service", 
        "description": "CPU-intensive factorial calculations",
        "endpoints": {
            "/factorial/{n}": "Calculate factorial",
            "/prime/{n}": "Compatibility endpoint (calculates factorial)"
        }
    }