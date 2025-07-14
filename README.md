# Factorial Service - Microservice Scaling Analysis

**Factorial Service** è un microservizio scritto in Python (FastAPI) per l'analisi completa del comportamento di scaling orizzontale. Include monitoraggio Prometheus, test di carico automatizzati e generazione di dataset per analisi di performance e capacity planning.

---

## 📦 Struttura del Progetto

```
factorial-service/
├── .gitignore
├── Dockerfile                          # Multi-worker container setup
├── README.md                          # Documentazione completa
├── requirements.txt                   # Dipendenze Python
├── kube-state-metrics.yaml          # Metriche Kubernetes
├── src/
│   └── factorial_service.py         # Servizio FastAPI CPU-intensive
├── scripts/
│   ├── simulate_and_collect.py      # Script principale di analisi scaling
│   ├── quick_test.py               # Test di verifica rapido
│   └── bottleneck_diagnosis.py     # Diagnosi problemi performance
├── k8s/
│   ├── namespace.yaml              # Namespace isolato
│   ├── deployment.yaml             # Deployment multi-replica
│   ├── service.yaml                # Service con LoadBalancer/NodePort
│   └── hpa.yaml                    # Horizontal Pod Autoscaler
└── prometheus/
    ├── prometheus-configmap.yaml   # Configurazione per metriche per-pod
    ├── prometheus-deployment.yaml  # Prometheus con RBAC completo
    └── prometheus-service.yaml     # Prometheus service
```

---

## 🎯 Caratteristiche Principali

### ✅ **Servizio FastAPI Ottimizzato**
- **CPU-intensive factorial calculations** con carichi realistici
- **Multi-worker support** (4 worker per default)
- **Metriche Prometheus** integrate (requests, latency, in-progress)
- **Health checks** e endpoint diagnostici

### ✅ **Analisi Scaling Completa**
- **Test automatizzati** per 1-8 repliche
- **Load balancing verification** con distribuzione per-pod
- **25+ metriche** per test (performance, latency, resources, power)
- **Dataset ML-ready** per capacity planning

### ✅ **Monitoring Avanzato**
- **Per-pod metrics collection** con Prometheus
- **CPU, Memory, Network monitoring**
- **Load distribution analysis**
- **Power efficiency calculations**

### ✅ **Production-Ready**
- **Auto-connectivity detection** (minikube service/port-forward)
- **Robust error handling** e retry logic
- **Comprehensive result analysis**
- **Industry benchmark comparisons**

---

## ⚙️ Prerequisiti

### **Software Richiesto:**
- **Docker** per build delle immagini
- **kubectl** configurato
- **Minikube** o cluster Kubernetes
- **Python 3.8+** per gli script di analisi

### **Risorse Cluster:**
- **CPU**: 4+ cores raccomandati per testing multi-replica
- **Memory**: 4GB+ per eseguire fino a 8 repliche
- **Storage**: 1GB per logs e dataset

---

## 🚀 Setup e Installazione

### **1. Clone del Repository**
```bash
git clone https://github.com/FabioGallone/factorial-service.git
cd factorial-service
```

### **2. Setup Minikube (Windows/Linux)**

**Windows:**
```powershell
# Scarica da: https://minikube.sigs.k8s.io/docs/start/
minikube start --cpus=4 --memory=4096
```

**Linux:**
```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube start --cpus=4 --memory=4096
```

### **3. Build e Deploy**
```bash
# Configura Docker per Minikube
eval $(minikube docker-env)  # Linux/Mac
# oppure
minikube docker-env | Invoke-Expression  # Windows PowerShell

# Build dell'immagine
docker build -t factorial-service:v1.0.0 .

# Deploy del namespace e servizi
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Deploy monitoring
kubectl apply -f kube-state-metrics.yaml
kubectl apply -f prometheus/prometheus-configmap.yaml
kubectl apply -f prometheus/prometheus-deployment.yaml
kubectl apply -f prometheus/prometheus-service.yaml
```

### **4. Verifica Deploy**
```bash
# Controlla i pod
kubectl get pods -n factorial-service

# Verifica servizi
kubectl get services -n factorial-service
```

---

## 🔧 Configurazione Connectivity

Il sistema supporta **multiple modalità di accesso** con auto-detection:

### **Opzione A: Minikube Service (Raccomandato)**
```bash
# Terminale 1: Servizio API
minikube service factorial-service -n factorial-service --url
# Mantieni aperto!

# Terminale 2: Prometheus
kubectl port-forward -n factorial-service service/prometheus 9090:9090

#Terminale 3
kubectl port-forward -n factorial-service service/factorial-service 8080:80
```

### **Opzione B: Minikube Tunnel**
```bash
# Terminale 1 (come Administrator)
minikube tunnel

# Terminale 2: Prometheus
kubectl port-forward -n factorial-service service/prometheus 9090:9090
```

### **Opzione C: LoadBalancer Service**
```bash
# Modifica k8s/service.yaml per type: LoadBalancer
kubectl apply -f k8s/service.yaml

# Aspetta external IP
kubectl get service factorial-service -n factorial-service -w
```

### **Opzione D: Port-Forward (Fallback)**
```bash
# Terminale 1: API
kubectl port-forward -n factorial-service service/factorial-service 8080:80

# Terminale 2: Prometheus
kubectl port-forward -n factorial-service service/prometheus 9090:9090
```

---

## 📊 Analisi Scaling

### **Script Principale di Analisi**
```bash
python scripts/simulate_and_collect.py
```

**Output:**
- **CSV completo** con 25+ metriche per test
- **Scaling efficiency analysis**
- **Load balancing assessment**
- **Power consumption insights**
- **Production readiness evaluation**

### **Configurazioni Personalizzate**

**Test Veloce (15 minuti):**
```python
replica_configs = [1, 2, 3, 4]
tests_per_replica = 2
```

**Test Approfondito (40 minuti):**
```python
replica_configs = [1, 2, 3, 4, 5, 6]
tests_per_replica = 5
```

**Test High-Scale (60+ minuti):**
```python
replica_configs = [1, 2, 3, 4, 5, 6, 7, 8]
tests_per_replica = 3
```

### **Script di Supporto**

**Diagnosi Performance:**
```bash
python scripts/bottleneck_diagnosis.py
```

---

## 📈 Metriche e Dataset

### **Metriche per Test (25 colonne CSV):**

| Categoria | Metriche |
|-----------|----------|
| **Performance** | RPS, latency (avg/max/p95), success rate |
| **Scaling** | Efficiency vs baseline, scale factor, per-replica RPS |
| **Resources** | CPU%, Memory%, load balancing status |
| **Load** | Concurrent users, total requests, complexity distribution |
| **Power** | Power per container, total power, power efficiency |
| **Timing** | Test duration, response time inflation |

### **Esempio Output:**
```csv
timestamp,replicas,req_per_sec,scaling_efficiency_vs_baseline,load_balanced
1752528066,1,84.6,100.0,True
1752528115,2,127.8,75.5,False
1752528162,3,137.4,54.2,False
1752528211,4,151.4,44.7,False
```

### **Benchmark Industriali:**
- **Excellent**: >80% scaling efficiency
- **Good**: 60-80% scaling efficiency ← **Target Zone**
- **Moderate**: 40-60% scaling efficiency
- **Poor**: <40% scaling efficiency

---

## 🎯 Risultati di Esempio

### **Performance Scaling Tipica:**
```
1 replica:  85 RPS (baseline, 100% efficiency)
2 repliche: 128 RPS (75% efficiency - GOOD!)
3 repliche: 137 RPS (54% efficiency - moderate)
4 repliche: 151 RPS (45% efficiency - acceptable)
```

### **Load Balancing Analysis:**
```
✅ 1 replica: Load balanced = True (normal)
❌ 2+ repliche: Load balanced = False (investigate)
   Pod principal: 97-99% traffic
   Pod secondary: 1-3% traffic
```

### **Assessment Automatico:**
- **75% efficiency** → "GOOD! Production-ready with solid scaling"
- **45% efficiency** → "MODERATE. Consider optimization"
- **25% efficiency** → "POOR. Investigation needed"

**🎯 Factorial Service - Production-ready microservice scaling analysis platform**