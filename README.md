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

* **Python 3.8+**
* **Docker** (per il container)
* **kubectl** e **un cluster Kubernetes** (min. v1.20+)
* **Prometheus** (opzionale, per il monitoraggio)

---

## 🚀 Esecuzione in locale (senza Docker)

1. **Clona il repository**

   ```bash
   git clone https://github.com/<tuo-utente>/prime-service.git
   cd prime-service
   ```

2. **Crea e attiva un ambiente virtuale**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Installa le dipendenze**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Avvia il servizio**

   ```bash
   uvicorn src.prime_service:app --host 0.0.0.0 --port 8000
   ```

   * L’API sarà disponibile su `http://localhost:8000`
   * Le metriche Prometheus su `http://localhost:8000/metrics`

---

## 🐳 Esecuzione con Docker

1. **Build dell’immagine**

   ```bash
   docker build -t prime-service:latest .
   ```

2. **Avvio del container**

   ```bash
   docker run -d \
     --name prime-service \
     -p 8000:8000 \
     prime-service:latest
   ```

   * API: `http://localhost:8000`
   * Metricas: `http://localhost:8000/metrics`

---

## ☸️ Deploy su Kubernetes

1. **Crea il namespace**

   ```bash
   kubectl apply -f k8s/namespace.yaml
   ```

2. **Deploy del servizio**

   ```bash
   kubectl apply -n prime-service -f k8s/deployment.yaml
   kubectl apply -n prime-service -f k8s/service.yaml
   ```

3. **Configura l’Horizontal Pod Autoscaler (HPA)**

   ```bash
   kubectl apply -n prime-service -f k8s/hpa.yaml
   ```

4. **Installa/aggiorna Prometheus (opzionale)**

   ```bash
   kubectl apply -n prime-service -f prometheus/prometheus-configmap.yaml
   kubectl apply -n prime-service -f prometheus/prometheus-deployment.yaml
   kubectl apply -n prime-service -f prometheus/prometheus-service.yaml
   ```

   * Prometheus inizierà a fare scrape delle metriche esposte dal servizio.

---

## 🔄 Simulazione di carico e raccolta metriche

Per testare il servizio e popolare Prometheus:

1. Assicurati di aver installato le dipendenze (vedi **Esecuzione in locale**).
2. **Esegui lo script**

   ```bash
   python scripts/simulate_and_collect.py
   ```

   * Lo script usa il dataset `scripts/prime_dataset.csv` per invocare ripetutamente l’API.
   * Le metriche raccolte verranno inviate a Prometheus (configurato in `simulate_and_collect.py`).

---

## 📑 File principali

* **`src/prime_service.py`**

  * FastAPI app con endpoint per il calcolo di numeri primi e metriche Prometheus.

* **`scripts/simulate_and_collect.py`**

  * Script di simulazione che genera richieste all’API e invia metriche personalizzate.

* **`k8s/`**

  * Manifests per namespace, deployment, service e HPA.

* **`prometheus/`**

  * Manifests per configurare Prometheus nel cluster Kubernetes.

---

## 📄 Licenza

Questo progetto è rilasciato sotto licenza MIT. Consulta il file `LICENSE` per maggiori dettagli.
