# Prime Service

**Prime Service** è un microservizio scritto in Python (FastAPI) che espone un’API per il calcolo di numeri primi e metriche Prometheus per il monitoraggio. Include inoltre uno script di simulazione per generare carico e raccogliere metriche.

---

## 📦 Struttura del progetto

```
prime-service/
├── .gitignore
├── Dockerfile
├── README.md
├── requirements.txt
├── src/
│   └── prime_service.py
├── scripts/
│   ├── prime_dataset.csv
│   └── simulate_and_collect.py
├── k8s/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
└── prometheus/
    ├── prometheus-configmap.yaml
    ├── prometheus-deployment.yaml
    └── prometheus-service.yaml
```

---

## ⚙️ Prerequisiti

* **kubectl**
* **Minikube** (o altro cluster Kubernetes)
* **Python 3.8+** (solo per lo script di simulazione)

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

1. **Clona il repository**

```bash
git clone https://github.com/FabioGallone/prime-service.git
cd prime-service
```

2. **Crea il namespace**

```bash
kubectl apply -f k8s/namespace.yaml
```

3. **Deploy del servizio**

```bash
kubectl apply -n prime-service -f k8s/deployment.yaml
kubectl apply -n prime-service -f k8s/service.yaml
```

4. **Configura l'Horizontal Pod Autoscaler (HPA)**

```bash
kubectl apply -n prime-service -f k8s/hpa.yaml
```

5. **Installa Prometheus nel cluster (opzionale)**

```bash
kubectl apply -n prime-service -f prometheus/prometheus-configmap.yaml
kubectl apply -n prime-service -f prometheus/prometheus-deployment.yaml
kubectl apply -n prime-service -f prometheus/prometheus-service.yaml
```

6. **Esporre le porte con `port-forward`**

In tre terminali distinti:

```bash
# Per accedere all'API FastAPI (porta 8080 -> servizio)
kubectl port-forward -n prime-service service/prime-service 8080:80
```

```bash
# Per accedere a Prometheus (porta 9090 -> Prometheus)
kubectl port-forward -n prime-service service/prometheus 9090:9090
```

```bash
# Per simulare carico con metrica push (porta 8001 -> FastAPI)
kubectl port-forward -n prime-service service/prime-service 8001:8001
```

* API disponibile su: `http://localhost:8080`
* Prometheus disponibile su: `http://localhost:9090`
* Endpoint di metrica custom push: `http://localhost:8001/metrics` (per lo script)

---

## 🔄 Simulazione di carico e raccolta metriche

1. **Installa le dipendenze Python**:

```bash
pip install -r requirements.txt
```

2. **Esegui lo script di simulazione**

```bash
python scripts/simulate_and_collect.py
```

* Lo script usa il dataset `scripts/prime_dataset.csv` per invocare ripetutamente l’API.
* Le metriche raccolte verranno inviate a Prometheus (configurato in `simulate_and_collect.py`).

---

