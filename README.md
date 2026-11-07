# 💰 FinTrack — Personal Finance Tracker

![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat&logo=chartdotjs&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white)

**FinTrack** is a sleek, lightweight web application designed to help you take control of your financial life. Built with a robust Flask backend and a responsive vanilla JS frontend, it offers real-time insights into your spending habits through interactive visualizations.

---

## ✨ Key Features

* **🔐 Secure Authentication** — Robust register/login system to keep your financial data private.
* **📊 Dynamic Dashboard** — Instant overview of your total balance, monthly income, and expenses.
* **📈 Interactive Analytics** — Powered by **Chart.js**, visualize category breakdowns (Pie) and monthly trends (Bar).
* **📂 Smart Categorization** — Organize transactions into custom categories like Food, Transport, and Utilities.
* **📱 Fully Responsive** — Manage your budget seamlessly across Desktop, Tablet, and Mobile.
* **🔍 Advanced Filtering** — Search through history or filter by date and category with ease.

---

## 📸 Product Showroom

| Light Mode                                          | Dark Mode                                           |
| :-------------------------------------------------- | :-------------------------------------------------- |
| <img src="screenshots/dashboard-light.png" width="100%" /> | <img src="screenshots/dashboard-dark.png" width="100%" /> |

---

## 🛠 Tech Stack

| Layer        | Technologies                    |
| :----------- | :------------------------------ |
| **Backend**  | Flask (Python), MySQL           |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Visuals**  | Chart.js, FontAwesome           |
| **Security** | Werkzeug Hashing                |

---

## 🚀 Getting Started

### 1. Prerequisites

* Python **3.8+**
* MySQL Server running locally

### 2. Database Configuration

```sql
-- 1. Create the database
CREATE DATABASE finance_db;

-- 2. Import the schema
-- Run the provided db.sql file using your MySQL client
SOURCE path/to/db.sql;
```

### 3. Installation & Launch

```bash
# Clone the repository
git clone https://github.com/yourusername/FinTrack.git
cd FinTrack

# Install dependencies
pip install -r requirements.txt

# Configure credentials in app.py
# host="localhost", user="root", password="your_password"

# Run the server
python app.py
```

Visit the app at: **http://127.0.0.1:5000/**


