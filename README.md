# Prime Service

**Prime Service** è un microservizio scritto in Python (FastAPI) che espone un'API per il calcolo di numeri primi e metriche Prometheus per il monitoraggio. Include inoltre uno script di simulazione per generare carico e raccogliere metriche complete di CPU, memoria e replica count.

---

## 📦 Struttura del progetto

```
prime-service/
├── .gitignore
├── Dockerfile
├── README.md
├── requirements.txt
├── kube-state-metrics.yaml          # Nuovo: per metriche Kubernetes
├── src/
│   └── prime_service.py
├── scripts/
│   ├── prime_dataset.csv
│   ├── simulate_and_collect.py
│   └── simulate_and_collect_improved.py  # Nuovo: versione migliorata
├── k8s/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
└── prometheus/
    ├── prometheus-configmap.yaml    # Aggiornato: configurazione completa
    ├── prometheus-deployment.yaml   # Aggiornato: con RBAC
    └── prometheus-service.yaml
```

---

## ⚙️ Prerequisiti

* **kubectl**
* **Minikube** (o altro cluster Kubernetes)
* **Python 3.8+** (solo per lo script di simulazione)

### 🔧 Installazione di Minikube

#### Su **Windows**:

1. Scarica l'installer da:
   [https://minikube.sigs.k8s.io/docs/start/](https://minikube.sigs.k8s.io/docs/start/)
2. Installa e verifica:

   ```powershell
   minikube version
   minikube start
   ```

#### Su **Linux**:

```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube start
```

---

## ☘️ Deploy su Kubernetes con Minikube

### 1. **Setup iniziale**

```bash
git clone https://github.com/FabioGallone/prime-service.git
cd prime-service

# Configura Docker per usare il registry di Minikube
eval $(minikube docker-env)  # Linux/Mac
# oppure
minikube docker-env | Invoke-Expression  # Windows PowerShell

# Costruisci l'immagine Docker
docker build -t prime-service:v1.0.0 .
```

### 2. **Deploy del namespace e servizi base**

```bash
# Crea il namespace
kubectl apply -f k8s/namespace.yaml

# Deploy del servizio principale
kubectl apply -n prime-service -f k8s/deployment.yaml
kubectl apply -n prime-service -f k8s/service.yaml

# Configura l'Horizontal Pod Autoscaler (HPA)
kubectl apply -n prime-service -f k8s/hpa.yaml
```

### 3. **Installa kube-state-metrics (IMPORTANTE per le metriche)**

```bash
# Installa kube-state-metrics per ottenere metriche sui deployment
kubectl apply -f kube-state-metrics.yaml
```

### 4. **Deploy di Prometheus con configurazione completa**

```bash
# Applica la configurazione Prometheus aggiornata
kubectl apply -f prometheus/prometheus-configmap.yaml

# Deploy Prometheus con RBAC (autorizzazioni necessarie)
kubectl apply -f prometheus/prometheus-deployment.yaml
kubectl apply -f prometheus/prometheus-service.yaml
```

### 5. **Verifica che tutto sia in esecuzione**

```bash
# Controlla i pod nel namespace prime-service
kubectl get pods -n prime-service

# Controlla kube-state-metrics
kubectl get pods -n kube-system

# Verifica i logs di Prometheus
kubectl logs -n prime-service deployment/prometheus-deployment
```

### 6. **Esporre le porte con port-forward**

Apri **tre terminali distinti** ed esegui:

**Terminale 1 - API FastAPI:**
```bash
kubectl port-forward -n prime-service service/prime-service 8080:80
```

**Terminale 2 - Prometheus UI:**
```bash
kubectl port-forward -n prime-service service/prometheus 9090:9090
```

**Terminale 3 - Metriche endpoint:**
```bash
kubectl port-forward -n prime-service service/prime-service 8001:8001
```

### 7. **Verifica degli endpoint**

* **API disponibile su:** `http://localhost:8080`
  - Test: `http://localhost:8080/prime/17`
* **Prometheus UI:** `http://localhost:9090`
  - Verifica nella sezione "Targets" che i servizi siano raggiungibili
* **Metriche endpoint:** `http://localhost:8001/metrics`

---

## 🔄 Simulazione di carico e raccolta metriche

### 1. **Installa le dipendenze Python:**

```bash
pip install -r requirements.txt
```

### 2. **Verifica configurazione Prometheus**

Prima di eseguire lo script, verifica che Prometheus stia raccogliendo le metriche:

1. Vai su `http://localhost:9090`
2. Nella sezione **Targets**, verifica che siano presenti e **UP**:
   - `prime-service` (per le metriche custom)
   - `kubernetes-cadvisor` (per CPU/memoria)
   - `kube-state-metrics` (per replica count)
3. Prova queste query nel **Query Browser**:
   - `up` (tutti i target attivi)
   - `prime_requests_total` (metriche del servizio)
   - `container_memory_working_set_bytes` (memoria container)
   - `kube_deployment_status_replicas` (numero repliche)

### 3. **Esegui lo script di simulazione**

**Script base (originale):**
```bash
python scripts/simulate_and_collect.py
```



### 4. **Output aspettato**

Lo script dovrebbe mostrare output simile a:
```
=== DEBUG: Metriche disponibili ===
✓ prime_requests_total: 1 serie(s) disponibili
✓ container_memory_working_set_bytes: 12 serie(s) disponibili
Query funzionante: sum(container_memory_working_set_bytes{namespace="prime-service"})

Iteration 0: RPS=156.45, Latency=0.0581s, CPU=0.120, Memory=134217728, Replicas=1
```

---


## 📊 Metriche disponibili

### **Metriche custom del servizio:**
- `prime_requests_total` - Totale richieste ricevute
- `prime_inprogress_requests` - Richieste in corso
- `prime_request_latency_seconds` - Istogramma latenze

### **Metriche sistema (tramite cAdvisor):**
- `container_cpu_usage_seconds_total` - Utilizzo CPU
- `container_memory_working_set_bytes` - Memoria utilizzata

### **Metriche Kubernetes (tramite kube-state-metrics):**
- `kube_deployment_status_replicas` - Numero repliche
- `kube_pod_info` - Informazioni sui pod

---

## 🔧 Configurazione avanzata

### **Modifica intervallo di scraping Prometheus:**
Edita `prometheus/prometheus-configmap.yaml` e cambia `scrape_interval`

### **Modifica soglia HPA:**
Edita `k8s/hpa.yaml` e cambia `averageUtilization`

### **Modifica risorse container:**
Edita `k8s/deployment.yaml` nella sezione `resources`

---

## 📝 Note

- Il dataset viene salvato in `scripts/prime_dataset.csv`
- Le metriche sono raccolte ogni 5 secondi per default
- L'HPA è configurato per scalare tra 1-10 repliche al 50% CPU
- kube-state-metrics è installato nel namespace `kube-system`
- Prometheus ha accesso cluster-wide tramite RBAC per raccogliere tutte le metriche