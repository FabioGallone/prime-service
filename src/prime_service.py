from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time
import threading

app = FastAPI()

# Metriche Prometheus
REQ_COUNTER = Counter('prime_requests_total', 'Richieste totali ricevute')
IN_PROGRESS = Gauge('prime_inprogress_requests', 'Richieste in corso')
LATENCY = Histogram('prime_request_latency_seconds', 'Istogramma delle latenze')

def run_metrics_server():
    start_http_server(8001)

threading.Thread(target=run_metrics_server, daemon=True).start()

def is_prime(n: int) -> bool:
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    p = 3
    while p * p <= n:
        if n % p == 0:
            return False
        p += 2
    return True

@app.get("/prime/{n}")
def check_prime(n: int):
    REQ_COUNTER.inc()
    IN_PROGRESS.inc()
    start = time.time()
    try:
        result = is_prime(n)
    finally:
        elapsed = time.time() - start
        LATENCY.observe(elapsed)
        IN_PROGRESS.dec()
    return {"number": n, "is_prime": result, "latency": elapsed}