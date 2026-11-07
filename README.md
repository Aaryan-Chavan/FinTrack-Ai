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

## ✨ Core Capabilities

* **Financial Treasury Dashboard:** Real-time ledger audit, cashflow variance, and monthly surplus telemetry featuring dynamic running-balance wave charts.
* **Node 402 Authentication:** Encrypted dual-factor authentication gateway capturing verified legal identities for institutional ledger governance.
* **Ledger Synchronization:** Cryptographically verified transaction feeds allowing users to seamlessly inject credit and debit events into the primary database.
* **Enterprise Salary Planner:** Algorithmic cash assignment based on the priority waterfall rule (Take-Home → Essentials → Debt → Emergency → Investments).
* **Month Closure & Reconciliation:** Reconcile internal book surplus against physical core banking reserves to seal the ledger for the fiscal month.
* **Autonomous Wealth Intelligence:** Context-aware AI copilot powered by Google Gemini that analyzes active records to output deterministic budget forecasts.
* **Verified Financial Instruments:** Curated, regulated asset vehicles (FDs, PPF, Index Funds) evaluated against the user's active monthly surplus.
* **Multi-Tenant Identity Management:** Comprehensive parameter controls, including dark/light mode toggling and secure session management.

---

## 📸 Application Gallery

### Dashboard & Analytics
<img src="ScreenShots/Screenshot 2026-11-07 152029.png" width="100%" alt="FinTrack Dashboard" />

### Ledger & Budget Planning
<p align="center">
  <img src="ScreenShots/Screenshot 2026-11-07 152111.png" width="49%" alt="Ledger Synchronization" />
  <img src="ScreenShots/Screenshot 2026-11-07 152129.png" width="49%" alt="Enterprise Salary Planner" />
</p>

### AI Copilot & Reconciliation
<p align="center">
  <img src="ScreenShots/Screenshot 2026-11-07 152304.png" width="49%" alt="AI Copilot Intelligence" />
  <img src="ScreenShots/Screenshot 2026-11-07 152226.png" width="49%" alt="Month Closure Reconciliation" />
</p>

### Financial Instruments & Profile Settings
<p align="center">
  <img src="ScreenShots/Screenshot 2026-11-07 152325.png" width="49%" alt="Financial Instruments" />
  <img src="ScreenShots/Screenshot 2026-11-07 152358.png" width="49%" alt="Profile Preferences" />
</p>

### Secure Authentication Gateway
<p align="center">
  <img src="ScreenShots/Screenshot 2026-11-07 152423.png" width="49%" alt="Sign In Gateway" />
  <img src="ScreenShots/Screenshot 2026-11-07 152442.png" width="49%" alt="Registration Gateway" />
</p>

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