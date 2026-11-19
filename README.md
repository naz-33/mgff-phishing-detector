# ZanderEtAlFishing — Automated Phishing Email Detection & Monitoring System

**Thesis Project:** *Automated Phishing Email Detection and Monitoring Using Multi-Granularity Feature Fusion with Hybrid Logistic Regression and LightGBM*

- **Phase 1 (Complete):** Production-grade ML inference engine powered by pre-trained model artifacts, dual-branch preprocessing, tri-granularity feature fusion (15,009 features), and 50/50 soft probability blending.
- **Phase 2 (Complete):** Google Gmail API OAuth 2.0 integration, MIME parsing, and automated background email monitoring with SQLite persistence.
- **Phase 3 (Incomplete):** Full-stack web monitoring dashboard (React, TypeScript, Tailwind CSS, Recharts) and secure REST API backend (FastAPI, Pydantic, JWT authentication, SQLite service).

---

## 1. System Architecture

```text
                               ┌────────────────────────────────┐
                               │       Google Gmail API         │
                               │  (OAuth 2.0 Read-Only Access)  │
                               └───────────────┬────────────────┘
                                               │ Polling / MIME Extraction
                                               ▼
                               ┌────────────────────────────────┐
                               │    Phase 2 Email Scanner       │
                               │      (monitor.py daemon)       │
                               └───────────────┬────────────────┘
                                               │ Raw / Lexical Text
                                               ▼
                               ┌────────────────────────────────┐
                               │  Phase 1 Hybrid ML Predictor   │
                               │   - Word TF-IDF (10,000)       │
                               │   - Char TF-IDF (5,000)        │
                               │   - 9 Stylometrics             │
                               │   - 50% LR + 50% LightGBM      │
                               └───────────────┬────────────────┘
                                               │ Probabilities & Latency
                                               ▼
                               ┌────────────────────────────────┐
                               │    SQLite Database (WAL Mode)  │
                               │   (zander_email_monitor.db)    │
                               └───────────────┬────────────────┘
                                               │ SQL Queries & Aggregations
                                               ▼
                               ┌────────────────────────────────┐
                               │    Phase 3 FastAPI Backend     │
                               │    - JWT Authentication        │
                               │    - Summary & Analytics APIs  │
                               │    - Monitored Email Logs      │
                               └───────────────┬────────────────┘
                                               │ RESTful JSON APIs
                                               ▼
                               ┌────────────────────────────────┐
                               │    Phase 3 React Dashboard     │
                               │  - Real-Time Security Monitor  │
                               │  - Email Inspection & Detail   │
                               │  - Research vs Live Analytics  │
                               │  - Settings & System Status    │
                               └────────────────────────────────┘
```

---

## 2. Project Directory Structure

```text
ZanderEtAlFishing/
│
├── backend/                         # Phase 3 FastAPI Backend API
│   ├── __init__.py
│   ├── app.py                       # FastAPI application & SPA static asset mount
│   ├── auth.py                      # PBKDF2 hashing, JWT access token creation/decode
│   ├── config.py                    # Environment & security configuration
│   ├── database_service.py          # SQLite database query and aggregation service
│   ├── schemas.py                   # Pydantic validation and response schemas
│   └── routers/
│       ├── __init__.py
│       ├── auth_routes.py           # /api/auth/login, /api/auth/me
│       ├── dashboard_routes.py      # /api/dashboard/summary
│       ├── emails_routes.py         # /api/emails, /api/emails/{id}
│       ├── analytics_routes.py      # /api/analytics/overview
│       ├── monitor_routes.py        # /api/monitor/status
│       └── model_routes.py          # /api/model/info
│
├── frontend/                        # Phase 3 React + TypeScript Frontend
│   ├── index.html                   # HTML template
│   ├── package.json                 # React, Vite, Tailwind CSS, Recharts, Lucide
│   ├── tailwind.config.js           # Cybersecurity dashboard color palette
│   ├── vite.config.ts               # Vite bundler & API proxy configuration
│   ├── src/
│   │   ├── App.tsx                  # Router & ProtectedRoute setup
│   │   ├── main.tsx                 # React entry point
│   │   ├── index.css                # Tailwind directives & base styling
│   │   ├── types.ts                 # TypeScript interfaces for API models
│   │   ├── context/
│   │   │   └── AuthContext.tsx      # Auth token state & session lifecycle
│   │   ├── services/
│   │   │   └── api.ts               # HTTP client with Bearer token injection
│   │   ├── components/Layout/
│   │   │   ├── Layout.tsx           # Responsive shell
│   │   │   ├── Navbar.tsx           # Target inbox, status pill, user menu
│   │   │   └── Sidebar.tsx          # Navigation links with Lucide icons
│   │   └── pages/
│   │       ├── Login.tsx            # Administrator login portal
│   │       ├── Dashboard.tsx        # KPI cards, recent alerts, recent scans table
│   │       ├── MonitoredEmails.tsx  # Filterable, searchable, paginated log
│   │       ├── EmailDetail.tsx      # 50/50 ensemble decomposition breakdown
│   │       ├── Analytics.tsx        # Time series, trends & research benchmark
│   │       └── Settings.tsx         # OAuth status, sync checkpoints, model info
│   └── dist/                        # Production build bundle (served by FastAPI)
│
├── models/                          # Trained model artifacts & config
│   ├── logistic_regression_model.joblib
│   ├── lightgbm_model.joblib
│   ├── word_vectorizer.joblib
│   ├── char_vectorizer.joblib
│   ├── scaler.joblib
│   ├── config.pkl                   # Original Colab research config (preserved)
│   └── inference_config.json        # 50/50 configuration
│
├── ml_engine/                       # Phase 1 ML prediction engine
│   ├── __init__.py
│   ├── model_loader.py              # Artifact loader and validation
│   ├── preprocessing.py             # Dual-branch text preprocessing pipeline
│   ├── feature_extraction.py        # 9 stylometrics and CSR feature fusion
│   └── predictor.py                 # Hybrid soft-blending predictor & predict_email()
│
├── gmail_integration/               # Phase 2 Gmail scanner service
│   ├── __init__.py
│   ├── auth.py                      # OAuth 2.0 flow & token management (read-only)
│   ├── gmail_client.py              # Gmail API client with retry and backoff logic
│   ├── email_parser.py              # MIME parsing, HTML-to-text conversion
│   └── scanner.py                   # Automated polling service & sync checkpointing
│
├── database/                        # Database connectivity & repository
│   ├── __init__.py
│   ├── connection.py                # SQLite connection factory & WAL configuration
│   └── repository.py                # CRUD operations for email scans & sync state
│
├── credentials/                     # OAuth credentials (excluded from git)
│   ├── credentials.json             # Google Cloud OAuth 2.0 Client Secrets JSON
│   └── token.json                   # Generated authorized user token
│
├── tests/                           # Complete test suite (75 passing tests)
│   ├── test_backend_api.py          # FastAPI endpoints, auth, and database queries
│   ├── test_compatibility.py        # Artifact compatibility & baseline replication
│   ├── test_email_parser.py         # MIME parsing, decoding, HTML stripping
│   ├── test_features.py             # Feature order, scaling, and fusion tests
│   ├── test_gmail_scanner.py        # Scanner pagination, error containment, retries
│   ├── test_predictor.py            # Output schema, 50/50 blend calculation
│   ├── test_preprocessing.py        # Dual-branch preprocessing tests
│   └── test_scan_storage.py         # SQLite schema & synchronization tests
│
├── main.py                          # Phase 1 Interactive CLI prediction tester
├── monitor.py                       # Phase 2 Automated Gmail email monitor
├── run_dashboard.py                 # Phase 3 Server launcher (API + Frontend)
├── requirements.txt                 # Pinned dependencies
├── .env.example                     # Environment configuration template
└── README.md                        # Documentation
```

---

## 3. Installation & Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Web Dashboard & API
```bash
python run_dashboard.py
```
- **Dashboard Web UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API Health Endpoint:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 3. Administrator Login Credentials
- **Username:** `admin`
- **Password:** `ZanderAdmin2026!`
*(Credentials can be customized using `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment variables).*

### 4. Optional: Run Frontend in Vite Development Mode
For live UI hot-reloading:
```bash
cd frontend
npm install
npm run dev
```
Accessible at [http://localhost:3000/](http://localhost:3000/) (automatically proxies `/api` calls to `127.0.0.1:8000`).

---

## 4. Running the Complete System End-to-End

The ZanderEtAlFishing architecture uses a decoupled service design:

### Terminal 1: Automated Gmail Scanner (Phase 2 Daemon)
```bash
python monitor.py --interval 60
```
- Connects to the authorized Gmail inbox.
- Polls for new messages every 60 seconds (or configured interval).
- Computes ML predictions and commits results into SQLite database `zander_email_monitor.db`.

### Terminal 2: Web Dashboard & Backend Server (Phase 3)
```bash
python run_dashboard.py
```
- Serves the modern cybersecurity dashboard.
- Serves REST API endpoints feeding the React UI directly from SQLite.
- Enables continuous monitoring, alert inspection, and historical analytics without interrupting scanner execution.

### Terminal 3: Interactive CLI Prediction Tester (Phase 1)
```bash
python main.py
```
- Interactive terminal tool to test manual email snippets against the hybrid model.

---

## 5. Web Dashboard Pages & Features

### 1. Security Monitoring Center (Dashboard)
- **Branding:** Official *ZanderEtAlFishing* cybersecurity theme.
- **KPI Metrics:** Total Scanned, Phishing Detections, Legitimate Detections, and Average Model Inference Latency.
- **Mailbox & Scanner Status:** Active target mailbox display with live connection pill.
- **Classification Ratio:** Visual donut chart of overall phishing threat percentage.
- **High Priority Phishing Warnings:** Prominent alerts for suspicious incoming messages.
- **Recent Monitored Emails Table:** Quick summary with direct links to full detection breakdowns.

### 2. Monitored Emails Log
- **Comprehensive Table:** Subject, Sender, Received Date, Final Classification, Phishing Probability, and Scanned Date.
- **Search:** Real-time search across subject and sender headers.
- **Classification Filter:** Quick dropdown filtering for All, Phishing threats only, or Legitimate emails only.
- **Sorting:** Multi-column sorting (Received Date, Scanned Date, Probability, Latency).
- **Pagination:** Clean page navigation handling hundreds of logged emails efficiently.
- **Color Coding:** Distinct high-visibility badges (Red: Phishing threat, Green: Legitimate email).

### 3. Email Detection Details
- **Verdict Banner:** Clear determination banner displaying final classification and ensemble probability.
- **Probability Breakdown:** Visual decomposition of Stream 1 (Logistic Regression) vs Stream 2 (LightGBM).
- **Ensemble Formula:** Clear presentation of the 50/50 probability blend:
  $$P_{\text{final}} = (0.50 \times P_{\text{LR}}) + (0.50 \times P_{\text{LightGBM}})$$
- **Metadata Details:** Subject, sender, message IDs, received timestamps, and exact inference latency in milliseconds.
- **Feature Pipeline Technical Specs:** Explains the Multi-Granularity extraction applied to the email (10,000 word n-grams, 5,000 char n-grams, 9 stylometric features).
- **Privacy Enforcement:** Raw email bodies are not exposed on client screens.

### 4. Analytics & Performance Telemetry
- **Operational Timeline:** Time-series area charts showing emails scanned and phishing alerts detected over time.
- **Latency Trend:** Line chart tracking model processing latency (ms) across scans.
- **Date Filtering:** Allows narrowing analysis to specific operational date ranges.
- **Separately Labeled Research Benchmark Section:**
  > [!IMPORTANT]
  > Operational monitoring statistics (from unlabeled Gmail streams) are strictly distinguished from publication-grade experimental evaluations.
- **Thesis Research Metrics Table:**
  - **Proposed Hybrid Framework:** Accuracy **99.12%**, Precision **0.9904**, Recall **0.9921**, F1-Score **0.9912**, ROC-AUC **0.9989**, Average Precision **0.9987**.
  - **Baseline Replication Model:** Accuracy **95.79%**, Precision **0.9528**, Recall **0.9437**, F1-Score **0.9482**.
  - **Performance Delta:** Statistically verified improvements across all metrics (+3.33% Accuracy, +0.0376 Precision, +0.0484 Recall, +0.0430 F1).
  - **Confusion Matrix Breakdown:** 6,052 True Negatives, 59 False Positives (0.48%), 49 False Negatives (0.40%), 6,116 True Positives on held-out test data.

### 5. Scanner & Architecture Settings
- **Connected Gmail Account:** Display of verified authorized mailbox (`nazlahnanding13@gmail.com`).
- **Authorization Health:** Confirms valid OAuth 2.0 token with `gmail.readonly` scope without revealing secret keys.
- **Scanner Synchronization Checkpoint:** Current internal date epoch millisecond sync baseline.
- **Machine Learning Architecture:** Confirms loaded `.joblib`/`.pkl` artifacts, threshold ($\tau = 0.50$), and 50/50 ensemble blending weights.

---

## 6. Backend REST API Endpoints

All data endpoints require JWT Bearer authentication except the `/api/health` and `/api/auth/login` routes.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health probe (database status, timestamp) |
| `POST` | `/api/auth/login` | Authenticate administrator & issue JWT token |
| `GET` | `/api/auth/me` | Current authenticated session profile |
| `GET` | `/api/dashboard/summary` | Top-level counts, latency, mailbox, recent alerts |
| `GET` | `/api/emails` | Paginated email records with search, filter, sort |
| `GET` | `/api/emails/{id}` | Detailed inspection for a specific email scan |
| `GET` | `/api/analytics/overview` | Time-series trends & research benchmark data |
| `GET` | `/api/monitor/status` | Scanner status, OAuth validity, sync checkpoints |
| `GET` | `/api/model/info` | Ensemble configuration, feature dimensions |

---

## 7. Security and Privacy Guarantees

1. **Strict Read-Only Scope:** Uses solely `https://www.googleapis.com/auth/gmail.readonly`. The system has zero capability to alter, send, or delete emails.
2. **Credential Protection:** Client secrets (`credentials.json`) and OAuth access/refresh tokens (`token.json`) are never sent over API endpoints, rendered in HTML, or committed to version control.
3. **Password Security:** Administrator authentication uses salted PBKDF2-HMAC-SHA256 (100,000 iterations) with signed JWT access tokens.
4. **Content Minimization:** Raw email bodies are processed in-memory during inference and are not stored in the database or transmitted over the monitoring API.

---

## 8. Verification and Test Suite

Run the complete test suite covering Phase 1, Phase 2, and Phase 3:

```bash
pytest -v
```

**Results:**
- **75 tests passing** (15 Phase 3 backend API tests, 60 Phase 1 & 2 ML and scanner tests).
- 100% test pass rate across dual-branch preprocessing, 15,009-dimension feature fusion, 50/50 ensemble probability blending, Gmail MIME parsing, SQLite WAL storage, JWT authentication, and REST API endpoints.
