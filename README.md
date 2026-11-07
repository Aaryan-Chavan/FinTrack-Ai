# 🚀 FinTrack-Ai — Autonomous Wealth Intelligence

![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![TiDB](https://img.shields.io/badge/TiDB_Cloud-3A73FF?style=flat&logo=tidb&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini_AI-4285F4?style=flat&logo=google&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat&logo=chartdotjs&logoColor=white)
![Render](https://img.shields.io/badge/Render_Deployed-46E3B7?style=flat&logo=render&logoColor=white)

**FinTrack-Ai** is an enterprise-grade, cloud-native personal finance application. Engineered with a Python/Flask backend and a distributed TiDB Serverless database, it features dynamic cashflow visualization and an integrated Google Gemini AI copilot for autonomous budget analysis.

---

## 📸 System Interface & Core Capabilities

### 1. Financial Treasury Dashboard
Real-time ledger audit, cashflow variance, and monthly surplus telemetry. Features a dynamic running-balance wave chart and proportionate category burn visualizations.
![FinTrack Dashboard](Screenshot%202026-11-07%20152029.jpg)

### 2. Node 402 Authentication & Registration
Encrypted dual-factor authentication gateway capturing verified legal identities for institutional ledger governance.
<p align="center">
  <img src="Screenshot%202026-11-07%20152423.png" width="48%" />
  <img src="Screenshot%202026-11-07%20152442.jpg" width="48%" />
</p>

### 3. Ledger Synchronization & Verification
Cryptographically verified transaction feeds allowing users to seamlessly inject credit and debit events into the primary database.
![Transactions](Screenshot%202026-11-07%20152111.png)

### 4. Enterprise Salary Planner
Algorithmic cash assignment based on the priority waterfall rule (Take-Home → Essentials → Debt → Emergency → Investments).
![Salary Planner](Screenshot%202026-11-07%20152129.jpg)

### 5. Month Closure & Reconciliation
Reconcile internal book surplus against physical core banking reserves to seal the ledger for the fiscal month.
![Month Closure](Screenshot%202026-11-07%20152226.jpg)

### 6. Autonomous Wealth Intelligence (AI Copilot)
Context-aware financial intelligence powered by Google Gemini. Analyzes active records to output deterministic budget forecasts and surplus distribution strategies.
![AI Assistant](Screenshot%202026-11-07%20152304.jpg)

### 7. Verified Financial Instruments
Curated, regulated asset vehicles (FDs, PPF, Index Funds, SCSS) evaluated against the user's active monthly surplus for actionable investment routing.
![Explore Products](Screenshot%202026-11-07%20152325.jpg)

### 8. Identity & Application Preferences
Multi-tenant ledger parameter controls, including dark/light mode toggling and session management.
![Profile Settings](Screenshot%202026-11-07%20152358.jpg)

---

## 🏗 Architecture & Technologies

| Component | Technology Stack | Functionality |
| :--- | :--- | :--- |
| **Backend API** | Python 3, Flask | Orchestrates RESTful endpoints, session management, and business logic routing. |
| **Database** | TiDB Cloud Serverless (MySQL) | Cloud-native distributed SQL database handling user records, transactions, and historical telemetry. |
| **AI Engine** | Google Gemini 2.5 Flash | Ingests contextual JSON ledgers to generate highly specific, grounded financial insights. |
| **Frontend UI** | HTML5, Tailwind CSS, Vanilla JS | Responsive, state-driven dashboard utilizing asynchronous fetch requests. |
| **Visualizations**| Chart.js | Renders dynamic sequential wave charts and comparative doughnut charts based on live ledger states. |
| **Deployment** | Render, Gunicorn | Production WSGI server securely passing injected environment variables to the cloud instance. |

---

## 🚀 Local Development Setup

### 1. Clone & Environment Activation
```bash
git clone [https://github.com/Aaryan-Chavan/FinTrack-Ai.git](https://github.com/Aaryan-Chavan/FinTrack-Ai.git)
cd FinTrack-Ai
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate