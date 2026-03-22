***

# 🟢 Punar.io: The Circular Electronics Exchange
### *Blockchain-Proven, AI-Verified, EPR-Compliant.*

**Punar.io** (Sanskrit for "Again") is a decentralized lifecycle management platform for e-waste. We bridge the gap between consumers, local micro-entrepreneurs (technicians), and global compliance standards (CPCB/EPR) using a transparent, trustless architecture.
https://final-project-nine-pearl.vercel.app/
---

## 🏗️ The Unified Architecture
The power of Punar.io lies in its three-layer synergy. Every gram of e-waste is accounted for from the moment a bill is uploaded to the final material recovery report.

<img width="1280" height="766" alt="image" src="https://github.com/user-attachments/assets/ba26d019-495d-4366-842c-068a4c8c7d79" />

### 1. The Verification Layer (AI & OCR)
* **Module:** `OCR_Bills`
* **Function:** Using a **PaddleOCR-driven pipeline**, we extract deterministic metadata (IMEI, Model, Purchase Date) from physical invoices. This acts as the "Genesis Block" for a device's digital twin, preventing fraudulent claims.

### 2. The Trust & Ledger Layer (Blockchain & Rewards)
* **Modules:** `main` & `reward-system`
* **Function:** Every state change—from **Intake** to **Triage** to **Refurbishment**—is hashed and anchored to the **Polygon Blockchain**. 


* **Incentive Loop:** Users earn **ReCoins** (via our Banking API) only when a Partner Technician verifies the physical "Intake" hash.
<img width="1280" height="766" alt="image" src="https://github.com/user-attachments/assets/e14e64ef-b63f-46e1-a6b3-f4c8e4a03e98" />


### 3. The Compliance Layer (EPR & ESG Data)
* **Module:** `epr-api`
* **Function:** Our API calculates the **Environmental Impact Score** ($CO_2$ saved, rare earth minerals recovered like $Au, Cu, Li$) based on the device's final state (Recycled vs. Refurbished).

<img width="1280" height="766" alt="image" src="https://github.com/user-attachments/assets/5e75563c-c799-4861-9ddc-419d2979d887" />


---
## System Workflow

<img width="1376" height="1170" alt="image" src="https://github.com/user-attachments/assets/3743b8b6-4b49-40df-8a65-2e0c2ed007e0" />

## 🔄 The Lifecycle Flow: From "Disown" to "Dispose"

Based on our system design, the device follows a strictly logged path:

### Phase A: Submission & Verification
1.  **User Upload:** The user submits photos and bill details.
2.  **AI Triage:** `OCR_Bills` parses the brand/model/date.
3.  **On-Chain Anchor:** A `LOG_HASH: SUBMITTED` is generated and pushed to the Blockchain Event Log.

### Phase B: Physical Intake & Decisioning
4.  **Partner Intake:** A technician performs an IMEI match and weight check.
5.  **Technician Decision:** A manual triage determines the device's fate:
    * **Path 1: Fully Functional:** Minor repairs $\rightarrow$ `LOG_HASH: REFURBISHED` $\rightarrow$ Listed on Marketplace.
    * **Path 2: Non-Functional:** Parts harvested $\rightarrow$ `LOG_HASH: PARTS_HARVESTED` $\rightarrow$ Listed as Spares.
    * **Path 3: End-of-Life:** No usable parts $\rightarrow$ `LOG_HASH: RECYCLED` $\rightarrow$ Sent to Authorized Recycler.

### Phase C: Impact & Compliance
6.  **Reward Distribution:** User is rewarded **ReCoins** (weighted by the device's condition/path).
7.  **Data Aggregation:** `epr-api` batches material recovery data for **OEM/Brand & Compliance Stakeholders**, providing a transparent audit trail for EPR credits.


---

## 🏗️ Service Architecture

<img width="1600" height="491" alt="image" src="https://github.com/user-attachments/assets/3d22e212-15ca-4770-8ed9-8991edfffb8c" />

---

## 📊 Impact Metrics
Our `epr-api` calculates the "Green Value" of every transaction using the following logic:

* **Refurbishment Path:** Prioritizes $CO_2$ displacement by extending product life.
* **Recycling Path:** Measures $kg$ of recovered materials (Circularity Index).

> **Note:** All impact data is cryptographically linked to the original device's IMEI verified during the OCR stage, ensuring **zero double-counting** of carbon credits.

---

## 🚀 Installation & Setup

## 📋 API Endpoints
<img width="1600" height="415" alt="image" src="https://github.com/user-attachments/assets/55938748-6f2d-4724-9ee9-13b74e4d5eae" />


### Rapid Deployment
```bash
# 1. Start the AI OCR Service
cd OCR_Bills && uvicorn app:app --port 8001

# 2. Start the EPR Compliance API
cd epr-api && uvicorn main:app --port 8000

# 3. Launch the Marketplace & Reward System
cd main && npm install && npm start
```

---

## 🏆 The "Punar" Advantage
* **Transparency:** No more "lost" e-waste; every step is on-chain.
* **Scalability:** Local tech shops act as decentralized intake centers.
* **Compliance:** Real-time dashboards for brands to track their EPR targets.

**





# 💳 Credit Card Reward System - Mock Bank API

A mock bank API that converts e-waste value into credit card reward points. Perfect for recycling platforms and hackathon projects.

---

## 🌟 Key Features

| Feature | Description |
|---------|-------------|
| **💰 Instant Points Conversion** | ₹1 = 10 points. A ₹500 device instantly becomes 5,000 reward points |
| **💳 Multi-Bank Support** | HDFC, ICICI, SBI with built-in card validation and test cards |
| **🔄 Idempotent Processing** | Unique reference IDs prevent duplicate points issuance |
| **📊 Transaction Tracking** | Full status history with unique transaction IDs |
| **🔌 Webhook Ready** | Settlement notifications with retry logic |
| **🛡️ Fraud Prevention** | Card validation, limits, duplicate checks, and risk scoring |
| **📖 Swagger UI** | Interactive API documentation |
| **🌐 CORS Enabled** | Ready for frontend integration |

---




## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check if API is running |
| GET | `/` | Welcome message |
| POST | `/api/rewards/issue` | Issue reward points |
| GET | `/api/rewards/transaction/{id}` | Get transaction status |
| GET | `/api/rewards/banks` | List supported banks |
| GET | `/api/admin/dashboard` | System statistics |
| GET | `/api/admin/transactions` | All transactions |

---

## Install Dependencies

```bash
   pip install -r requirements.txt
```



## 🔧 How to Use

### 1. Check if API is Running

```bash
curl https://localhost:3001/health

