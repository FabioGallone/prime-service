# Factorial Service - Microservice Scaling Analysis

**Factorial Service** è un microservizio scritto in Python (FastAPI) per l'analisi completa del comportamento di scaling orizzontale. Include monitoraggio Prometheus, test di carico automatizzati e generazione di dataset per analisi di performance e capacity planning.

## 🎯 Risultati Ottenuti

Attraverso un'analisi approfondita, sono stati raggiunti i seguenti risultati:

- **✅ Baseline Performance**: 677 RPS per replica
- **✅ Scaling Efficiency**: 59.8% (miglioramento di +11.8% rispetto alla configurazione iniziale)
- **✅ Load Balancing Issues Identificati**: Session affinity e worker overlap
- **✅ Production-Ready Dataset**: 25+ metriche per test con analisi completa

---

## 📦 Struttura del Progetto

```
factorial-service/
├── .gitignore
├── Dockerfile                          # Multi-worker container setup
├── README.md                          # Documentazione completa aggiornata
├── requirements.txt                   # Dipendenze Python
├── kube-state-metrics.yaml          # Metriche Kubernetes
├── src/
│   └── factorial_service.py         # Servizio FastAPI ottimizzato (v1.0.1)
├── scripts/
│   └── simulate_and_collect.py      # Script principale di analisi (VERSIONE FINALE)
├── k8s/
│   ├── namespace.yaml              # Namespace isolato
│   ├── deployment.yaml             # Deployment multi-replica
│   ├── service.yaml                # Service con ClusterIP
│   └── hpa.yaml                    # Horizontal Pod Autoscaler
└── prometheus/
    ├── prometheus-configmap.yaml   # Configurazione per metriche per-pod
    ├── prometheus-deployment.yaml  # Prometheus con RBAC completo
    └── prometheus-service.yaml     # Prometheus service
```

---

## 🚀 Setup e Installazione Completo

### **Prerequisiti**
- **Docker** per build delle immagini
- **kubectl** configurato
- **Minikube** o cluster Kubernetes
- **Python 3.8+** per gli script di analisi

### **1. Setup Minikube**

#### **Windows:**
```powershell
# Scarica da: https://minikube.sigs.k8s.io/docs/start/
minikube start --nodes=1 --profile=multinodo
# Se volessi specificare anche le risorse per ogni nodo, esempio:
minikube start --nodes=1 --profile=multinodo --cpus=4 --memory=4096
# Per aggiungere N nodi al cluster, eseguire N volte:
minikube node add --profile=multinodo
# Per vedere tutti i nodi presenti nel cluster, eseguire
kubectl get nodes
```

#### **Linux/Mac:**
```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube start --nodes=1 --profile=multinodo
# Se volessi specificare anche le risorse per ogni nodo, esempio:
minikube start --nodes=1 --profile=multinodo --cpus=4 --memory=4096
# Per aggiungere N nodi al cluster, eseguire N volte:
minikube node add --profile=multinodo
# Per vedere tutti i nodi presenti nel cluster, eseguire
kubectl get nodes

#Per aggiungere una label personalizzata per chiarezza a tutti i nodi creati, esempio con cluster di 4 nodi:
kubectl label node multinodo-m02 node-role.kubernetes.io/worker=worker
kubectl label node multinodo-m03 node-role.kubernetes.io/worker=worker
kubectl label node multinodo-m04 node-role.kubernetes.io/worker=worker


# JUST TO KNOW:
# Per cancellare un profilo specifico:
minikube delete --profile=multinodo
```


### **2. Clone e Build**
```bash
# Clone del repository
git clone https://github.com/FabioGallone/factorial-service.git
cd factorial-service

# Configura Docker per Minikube
eval $(minikube docker-env)  # Linux/Mac
# minikube docker-env | Invoke-Expression  # Windows PowerShell

# Build dell'immagine (versione aggiornata)
docker build -t factorial-service:v1.0.1 .
```

### **3. Deploy Kubernetes**
```bash
# Deploy namespace e servizi
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Deploy monitoring
kubectl apply -f kube-state-metrics.yaml
kubectl apply -f prometheus/prometheus-configmap.yaml
kubectl apply -f prometheus/prometheus-deployment.yaml
kubectl apply -f prometheus/prometheus-service.yaml

# Verifica deploy
kubectl get pods -n factorial-service
kubectl get services -n factorial-service
```

---

## 🔧 Configurazione Connettività (AGGIORNATA)

### **Opzione A: Minikube Service (Raccomandato)**
```bash
# Terminale 1: Servizio API (LASCIA APERTO)
minikube service factorial-service -n factorial-service --url
# Output: http://127.0.0.1:XXXXX (nota la porta)

# Terminale 2: Prometheus (opzionale)
kubectl port-forward -n factorial-service service/prometheus 9090:9090
```

### **Opzione B: Port-Forward (Alternativa)**
```bash
# Terminale 1: API
kubectl port-forward -n factorial-service service/factorial-service 8095:80

# Terminale 2: Prometheus
kubectl port-forward -n factorial-service service/prometheus 9090:9090
```

### **Verifica Connettività**
```bash
# Testa l'API (usa la porta corretta)
curl http://127.0.0.1:XXXXX/factorial/50

# Dovrebbe restituire JSON con worker_pid
```

---

## 📊 Esecuzione Analisi Scaling

### **1. Script Principale (AUTO-DETECTION)**
Il script principale ora include auto-detection dell'URL:
```bash
pip install -r requirements.txt
```

```bash
pip install -r requirements.txt
```

```bash
python scripts/simulate_and_collect.py
```



### **1. Configurazioni Test**

#### **Test Veloce (15 minuti):**
```python
replica_configs = [1, 2, 3]
tests_per_replica = 2
```

#### **Test Completo (25 minuti):**
```python
replica_configs = [1, 2, 3, 4]
tests_per_replica = 3
```

#### **Test Approfondito (40 minuti):**
```python
replica_configs = [1, 2, 3, 4, 5, 6]
tests_per_replica = 5
```

---

<<<<<<< HEAD




### **🎯 Valore del Progetto:**
Questo progetto dimostra un'analisi completa di microservice scaling, identificando sia le capacità dell'applicazione che i limiti dell'infrastruttura. I risultati forniscono una base solida per decisioni di produzione e capacity planning.

---

=======
>>>>>>> af21c48583de03fdf229ec5fc9b2f794acc93d01
## 📚 Documentazione Tecnica

- **Architettura**: FastAPI + Uvicorn multi-worker
- **Orchestrazione**: Kubernetes con Prometheus monitoring
- **Load Balancing**: ClusterIP service con session affinity analysis
- **Scaling**: Horizontal Pod Autoscaler ready
- **Monitoring**: 25+ metriche per performance analysis

**🎯 Factorial Service - Production-ready microservice scaling analysis platform**